# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import patch
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import User, Workspace, WorkspaceMember
from plane.license.models import Instance


@pytest.fixture
def unconfigured_instance(db):
    return Instance.objects.create(
        instance_name="Plane Community Edition",
        instance_id=uuid4().hex,
        current_version="test",
        last_checked_at=timezone.now(),
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestSingletonInstanceSetup:
    @patch("plane.license.api.views.setup.workspace_seed.delay")
    def test_setup_creates_workspace_and_canonical_admin_atomically(
        self,
        mock_workspace_seed,
        client,
        django_capture_on_commit_callbacks,
        unconfigured_instance,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(
                "/api/instances/setup/",
                {
                    "email": "owner@example.com",
                    "password": "correct-horse-battery-staple-2026!",
                    "first_name": "Owner",
                    "last_name": "User",
                    "company_name": "Acme Inc",
                    "is_telemetry_enabled": "True",
                },
            )

        assert response.status_code == status.HTTP_302_FOUND
        workspace = Workspace.objects.get()
        user = User.objects.get(email="owner@example.com")
        membership = WorkspaceMember.objects.get(workspace=workspace, member=user)
        assert workspace.name == "Acme Inc"
        assert workspace.slug == "acme-inc"
        assert membership.role == 20
        assert membership.is_active is True

        unconfigured_instance.refresh_from_db()
        assert unconfigured_instance.is_setup_done is True
        assert unconfigured_instance.instance_name == "Acme Inc"
        mock_workspace_seed.assert_called_once_with(workspace.id)

        admin_status = client.get("/api/users/me/workspace-admin/")
        assert admin_status.status_code == status.HTTP_200_OK
        assert admin_status.json() == {"is_workspace_admin": True}

    @patch("plane.license.api.views.setup.workspace_seed.delay")
    def test_setup_rejects_whitespace_only_workspace_name(
        self,
        mock_workspace_seed,
        client,
        unconfigured_instance,
    ):
        response = client.post(
            "/api/instances/setup/",
            {
                "email": "owner@example.com",
                "password": "correct-horse-battery-staple-2026!",
                "first_name": "Owner",
                "last_name": "User",
                "company_name": "   ",
            },
        )

        assert response.status_code == status.HTTP_302_FOUND
        assert Workspace.objects.count() == 0
        assert User.objects.filter(email="owner@example.com").count() == 0
        unconfigured_instance.refresh_from_db()
        assert unconfigured_instance.is_setup_done is False
        mock_workspace_seed.assert_not_called()

    def test_instance_workspace_create_route_is_disabled(
        self,
        session_client,
        workspace,
        unconfigured_instance,
    ):
        response = session_client.post(
            "/api/instances/workspaces/",
            {"name": "Second", "slug": "second"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Workspace.objects.count() == 1

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("post", "/api/instances/admins/sign-up/"),
            ("post", "/api/instances/admins/sign-in/"),
            ("delete", f"/api/instances/admins/{uuid4()}/"),
        ],
    )
    def test_legacy_instance_admin_routes_are_removed(self, client, method, path):
        response = getattr(client, method)(path)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_instance_workspace_endpoint_returns_single_object(
        self,
        session_client,
        workspace,
        unconfigured_instance,
    ):
        response = session_client.get("/api/instances/workspace/")

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert response.json()["id"] == str(workspace.id)


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkspaceAdministration:
    @pytest.mark.parametrize("role", [15, 20])
    def test_workspace_put_is_removed(
        self,
        api_client,
        workspace,
        role,
    ):
        member = User.objects.create(
            email=f"workspace-role-{role}@example.com",
            username=f"workspace-role-{role}",
            is_active=True,
        )
        WorkspaceMember.objects.create(
            workspace=workspace,
            member=member,
            role=role,
            is_active=True,
        )
        api_client.force_authenticate(member)

        response = api_client.put(
            f"/api/workspaces/{workspace.slug}/",
            {"name": "Unauthorized replacement", "slug": workspace.slug},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        workspace.refresh_from_db()
        assert workspace.name != "Unauthorized replacement"

    def test_workspace_admin_status_uses_workspace_contract(
        self,
        session_client,
        workspace,
        unconfigured_instance,
    ):
        response = session_client.get("/api/users/me/workspace-admin/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"is_workspace_admin": True}

    def test_normal_app_session_authorizes_instance_settings(
        self,
        client,
        workspace,
        unconfigured_instance,
        create_user,
    ):
        client.force_login(create_user)

        response = client.patch(
            "/api/instances/",
            {"instance_name": "Updated from app session"},
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_200_OK
        unconfigured_instance.refresh_from_db()
        assert unconfigured_instance.instance_name == "Updated from app session"

    def test_final_admin_cannot_be_demoted(
        self,
        session_client,
        workspace,
        unconfigured_instance,
        create_user,
    ):
        membership = WorkspaceMember.objects.get(workspace=workspace, member=create_user)

        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/members/{membership.id}/",
            {"role": 15},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        membership.refresh_from_db()
        assert membership.role == 20

    def test_admin_can_demote_another_admin(
        self,
        session_client,
        workspace,
        unconfigured_instance,
    ):
        other_admin = User.objects.create(
            email="other-admin@example.com",
            username="other-admin",
            is_active=True,
        )
        other_membership = WorkspaceMember.objects.create(
            workspace=workspace,
            member=other_admin,
            role=20,
            is_active=True,
        )

        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/members/{other_membership.id}/",
            {"role": 15},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        other_membership.refresh_from_db()
        assert other_membership.role == 15

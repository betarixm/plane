# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Regression tests for GHSA-hpgm-9r34-c4x5 / GHSA-25gg-cxm8-g7h9.

A project GUEST (or MEMBER) must not be able to (de)activate other project
members by PATCHing ``{"is_active": false}`` while omitting the ``role`` field.
Before the fix, every authorization guard in ``ProjectMemberViewSet.partial_update``
lived inside ``if "role" in request.data:`` and ``is_active`` was writable through
``ProjectMemberSerializer(fields="__all__")`` — so a guest could deactivate any
member, including admins, and take over the project.
"""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Project,
    ProjectMember,
    ExternalIdentity,
    IdentitySource,
    User,
    WorkspaceMember,
)


def _member_detail_url(project_id: uuid.UUID, pk: uuid.UUID) -> str:
    return f"/api/workspace/projects/{project_id}/members/{pk}/"


def _make_user(email: str) -> User:
    local_part = email.split("@")[0]
    return User.objects.create(email=email, username=local_part, first_name=local_part)


def _add_member(workspace, project, user, *, ws_role: int, project_role: int) -> ProjectMember:
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=ws_role, is_active=True)
    installation = IdentitySource.objects.get(workspace=workspace)
    ExternalIdentity.objects.create(
        user=user,
        source=installation,
        external_user_id=f"U{user.id.hex[:20].upper()}",
        source_generation=installation.generation,
    )
    return ProjectMember.objects.create(
        workspace=workspace, project=project, member=user, role=project_role, is_active=True
    )


@pytest.fixture
def project(db, workspace, create_user):
    """A project administered by ``create_user``."""
    installation = IdentitySource.objects.create(
        workspace=workspace,
        provider=IdentitySource.Provider.SLACK,
        external_organization_id="TSECURITY",
        external_organization_name="Security Slack",
    )
    ExternalIdentity.objects.create(
        user=create_user,
        source=installation,
        external_user_id="UOWNER",
        source_generation=installation.generation,
    )
    project = Project.objects.create(
        name="Secure Project",
        identifier="SEC",
        workspace=workspace,
        created_by=create_user,
    )
    # create_user is a workspace admin (role=20 via the workspace fixture);
    # make them a project ADMIN too — this is the takeover victim.
    ProjectMember.objects.create(
        workspace=workspace, project=project, member=create_user, role=20, is_active=True
    )
    return project


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectMemberIsActiveAuthz:
    def test_bulk_member_update_cannot_demote_the_last_project_admin(
        self,
        workspace,
        project,
        create_user,
    ):
        ProjectMember.objects.filter(project=project, member=create_user).update(
            is_active=False,
        )
        sole_admin = _make_user("sole-project-admin@plane.so")
        sole_admin_membership = _add_member(
            workspace,
            project,
            sole_admin,
            ws_role=15,
            project_role=20,
        )
        client = APIClient()
        client.force_authenticate(user=sole_admin)

        response = client.post(
            f"/api/workspace/projects/{project.id}/members/",
            {"members": [{"member_id": str(sole_admin.id), "role": 15}]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        sole_admin_membership.refresh_from_db()
        assert sole_admin_membership.role == 20
        assert sole_admin_membership.is_active is True

    def test_last_project_admin_cannot_leave(
        self,
        workspace,
        project,
        create_user,
    ):
        client = APIClient()
        client.force_authenticate(user=create_user)

        response = client.post(
            f"/api/workspace/projects/{project.id}/members/leave/"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert ProjectMember.objects.get(project=project, member=create_user).is_active is True

    def test_inherited_put_project_update_route_is_removed(
        self,
        workspace,
        project,
    ):
        outsider = _make_user("put-outsider@plane.so")
        WorkspaceMember.objects.create(
            workspace=workspace,
            member=outsider,
            role=5,
            is_active=True,
        )
        installation = IdentitySource.objects.get(workspace=workspace)
        ExternalIdentity.objects.create(
            user=outsider,
            source=installation,
            external_user_id="UPUTOUTSIDER",
            source_generation=installation.generation,
        )
        client = APIClient()
        client.force_authenticate(user=outsider)

        response = client.put(
            f"/api/workspace/projects/{project.id}/",
            {"name": "Unauthorized replacement"},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        project.refresh_from_db()
        assert project.name == "Secure Project"

    def test_bulk_create_cannot_promote_a_slack_guest_with_a_string_role(
        self,
        workspace,
        project,
        create_user,
    ):
        guest = _make_user("string-role-guest@plane.so")
        guest_membership = _add_member(
            workspace,
            project,
            guest,
            ws_role=5,
            project_role=5,
        )
        client = APIClient()
        client.force_authenticate(user=create_user)

        response = client.post(
            f"/api/workspace/projects/{project.id}/members/",
            {"members": [{"member_id": str(guest.id), "role": "20"}]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        guest_membership.refresh_from_db()
        assert guest_membership.role == 5

    def test_guest_cannot_soft_delete_admin_through_hidden_model_fields(
        self,
        workspace,
        project,
        create_user,
    ):
        attacker = _make_user("soft-delete-attacker@plane.so")
        _add_member(workspace, project, attacker, ws_role=15, project_role=5)
        victim = ProjectMember.objects.get(project=project, member=create_user)
        client = APIClient()
        client.force_authenticate(user=attacker)

        response = client.patch(
            _member_detail_url(project.id, victim.id),
            {"deleted_at": "2026-08-24T00:00:00Z"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        victim.refresh_from_db()
        assert victim.deleted_at is None
        assert victim.is_active is True

    def test_guest_cannot_deactivate_admin(self, workspace, project, create_user):
        """A project GUEST must not deactivate a project ADMIN via is_active."""
        attacker = _make_user("guest-attacker@plane.so")
        # non-workspace-admin (role 15) so is_workspace_admin bypass does not apply,
        # project GUEST (role 5)
        _add_member(workspace, project, attacker, ws_role=15, project_role=5)
        victim = ProjectMember.objects.get(project=project, member=create_user)

        client = APIClient()
        client.force_authenticate(user=attacker)
        response = client.patch(
            _member_detail_url(project.id, victim.id),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        victim.refresh_from_db()
        assert victim.is_active is True

    def test_member_cannot_deactivate_admin(self, workspace, project, create_user):
        """A project MEMBER must not deactivate a project ADMIN via is_active."""
        attacker = _make_user("member-attacker@plane.so")
        _add_member(workspace, project, attacker, ws_role=15, project_role=15)
        victim = ProjectMember.objects.get(project=project, member=create_user)

        client = APIClient()
        client.force_authenticate(user=attacker)
        response = client.patch(
            _member_detail_url(project.id, victim.id),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        victim.refresh_from_db()
        assert victim.is_active is True

    def test_guest_cannot_deactivate_peer_guest(self, workspace, project):
        """A GUEST cannot deactivate another GUEST either (role check applies to all)."""
        attacker = _make_user("guest-a@plane.so")
        peer = _make_user("guest-b@plane.so")
        _add_member(workspace, project, attacker, ws_role=15, project_role=5)
        peer_member = _add_member(workspace, project, peer, ws_role=15, project_role=5)

        client = APIClient()
        client.force_authenticate(user=attacker)
        response = client.patch(
            _member_detail_url(project.id, peer_member.id),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        peer_member.refresh_from_db()
        assert peer_member.is_active is True

    def test_project_admin_can_deactivate_member(self, workspace, project):
        """Positive control: a project ADMIN (non-workspace-admin) may deactivate a MEMBER."""
        admin = _make_user("project-admin@plane.so")
        target = _make_user("plain-member@plane.so")
        # admin is a workspace MEMBER (15) but project ADMIN (20) — exercises the
        # role-comparison guard rather than the workspace-admin bypass.
        _add_member(workspace, project, admin, ws_role=15, project_role=20)
        target_member = _add_member(workspace, project, target, ws_role=15, project_role=15)

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            _member_detail_url(project.id, target_member.id),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        target_member.refresh_from_db()
        assert target_member.is_active is False

    def test_workspace_admin_with_low_project_role_can_deactivate(self, workspace, project, create_user):
        """
        Positive control: the intended workspace-admin bypass is preserved.

        A workspace ADMIN (role 20) may deactivate any project member — even a
        project ADMIN — despite holding only a project GUEST role, because
        is_workspace_admin short-circuits the role-comparison guard. Locks in the
        bypass so future changes don't silently remove it.
        """
        ws_admin = _make_user("ws-admin@plane.so")
        backup_admin = _make_user("backup-project-admin@plane.so")
        # workspace ADMIN (20) but only a project GUEST (5)
        _add_member(workspace, project, ws_admin, ws_role=20, project_role=5)
        _add_member(workspace, project, backup_admin, ws_role=15, project_role=20)
        # victim is the project ADMIN (create_user) set up by the `project` fixture
        victim = ProjectMember.objects.get(project=project, member=create_user)

        client = APIClient()
        client.force_authenticate(user=ws_admin)
        response = client.patch(
            _member_detail_url(project.id, victim.id),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        victim.refresh_from_db()
        assert victim.is_active is False

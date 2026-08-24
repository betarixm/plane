# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from plane.authentication.utils.workspace_project_join import (
    process_workspace_project_invitations,
)
from plane.bgtasks.workspace_seed_task import workspace_seed
from plane.db.models import (
    Project,
    ProjectMember,
    ProjectMemberInvite,
    User,
    WorkspaceMember,
    WorkspaceMemberInvite,
)
from plane.utils.workspace_admin import workspace_admin_guard


@pytest.fixture
def bot_workspace_admin(workspace, create_bot_user):
    return WorkspaceMember.objects.create(
        workspace=workspace,
        member=create_bot_user,
        role=20,
        is_active=True,
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkspaceAdminMutationInvariant:
    def test_bot_cannot_use_workspace_admin_mutations_when_human_admins_remain(
        self,
        api_client,
        workspace,
        create_user,
        bot_workspace_admin,
    ):
        other_admin = User.objects.create(
            email="other-human-admin@example.com",
            username="other-human-admin",
            is_active=True,
        )
        other_membership = WorkspaceMember.objects.create(
            workspace=workspace,
            member=other_admin,
            role=20,
            is_active=True,
        )
        api_client.force_authenticate(bot_workspace_admin.member)

        member_response = api_client.patch(
            f"/api/workspaces/{workspace.slug}/members/{other_membership.id}/",
            {"role": 15},
            format="json",
        )
        workspace_response = api_client.patch(
            f"/api/workspaces/{workspace.slug}/",
            {"name": "Bot controlled workspace"},
            format="json",
        )

        assert member_response.status_code == status.HTTP_403_FORBIDDEN
        assert workspace_response.status_code == status.HTTP_403_FORBIDDEN
        other_membership.refresh_from_db()
        workspace.refresh_from_db()
        assert other_membership.role == 20
        assert workspace.name != "Bot controlled workspace"

    def test_bot_workspace_admin_cannot_use_project_admin_fallbacks(
        self,
        workspace,
        create_user,
        bot_workspace_admin,
    ):
        project = Project.objects.create(
            workspace=workspace,
            name="Human controlled project",
            identifier="HUMAN",
            created_by=create_user,
        )
        victim = ProjectMember.objects.create(
            workspace=workspace,
            project=project,
            member=create_user,
            role=20,
            is_active=True,
        )
        ProjectMember.objects.create(
            workspace=workspace,
            project=project,
            member=bot_workspace_admin.member,
            role=5,
            is_active=True,
        )
        bot_client = APIClient()
        bot_client.force_authenticate(bot_workspace_admin.member)

        project_response = bot_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/",
            {"name": "Bot controlled project"},
            format="json",
        )
        member_response = bot_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/members/{victim.id}/",
            {"is_active": False},
            format="json",
        )

        assert project_response.status_code == status.HTTP_403_FORBIDDEN
        assert member_response.status_code == status.HTTP_403_FORBIDDEN
        project.refresh_from_db()
        victim.refresh_from_db()
        assert project.name == "Human controlled project"
        assert victim.is_active is True

    @pytest.mark.parametrize(
        ("method", "payload"),
        [("patch", {"role": 15}), ("delete", None)],
    )
    def test_bot_admin_cannot_remove_or_demote_final_human_admin(
        self,
        method,
        payload,
        workspace,
        create_user,
        bot_workspace_admin,
    ):
        human_membership = WorkspaceMember.objects.get(
            workspace=workspace,
            member=create_user,
        )
        bot_client = APIClient()
        bot_client.force_authenticate(bot_workspace_admin.member)
        url = f"/api/workspaces/{workspace.slug}/members/{human_membership.id}/"

        if method == "patch":
            response = bot_client.patch(url, payload, format="json")
        else:
            response = bot_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        human_membership.refresh_from_db()
        assert human_membership.role == 20
        assert human_membership.is_active is True

    def test_seed_style_bot_admin_does_not_allow_final_human_to_leave(
        self,
        session_client,
        workspace,
        create_user,
        bot_workspace_admin,
    ):
        response = session_client.post(f"/api/workspaces/{workspace.slug}/members/leave/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        membership = WorkspaceMember.objects.get(
            workspace=workspace,
            member=create_user,
        )
        assert membership.is_active is True

    @patch("plane.app.views.user.base.UserEndpoint._deactivate_user")
    def test_non_member_deactivation_still_uses_singleton_workspace_lock(
        self,
        mock_deactivate_user,
        api_client,
        workspace,
    ):
        user = User.objects.create(
            email="non-member@example.com",
            username="non-member",
            is_active=True,
        )
        api_client.force_authenticate(user)
        mock_deactivate_user.return_value = Response(status=status.HTTP_204_NO_CONTENT)

        with patch(
            "plane.app.views.user.base.workspace_admin_guard",
            wraps=workspace_admin_guard,
        ) as mock_guard:
            response = api_client.delete("/api/users/me/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_guard.assert_called_once_with(workspace_id=workspace.id)


@pytest.mark.contract
@pytest.mark.django_db
class TestInvitationAdminRolePreservation:
    def test_regular_member_cannot_manage_workspace_invitations(
        self,
        workspace,
    ):
        member = User.objects.create(
            email="member@example.com",
            username="member",
            is_active=True,
        )
        WorkspaceMember.objects.create(
            workspace=workspace,
            member=member,
            role=15,
            is_active=True,
        )
        invitation = WorkspaceMemberInvite.objects.create(
            workspace=workspace,
            email="invitee@example.com",
            token="member-created-token",
            role=15,
            created_by=member,
        )
        member_client = APIClient()
        member_client.force_authenticate(member)
        collection_url = f"/api/workspaces/{workspace.slug}/invitations/"
        detail_url = f"{collection_url}{invitation.id}/"

        create_response = member_client.post(
            collection_url,
            {"emails": [{"email": "another@example.com", "role": 15}]},
            format="json",
        )
        update_response = member_client.patch(detail_url, {"role": 20}, format="json")
        delete_response = member_client.delete(detail_url)

        assert create_response.status_code == status.HTTP_403_FORBIDDEN
        assert update_response.status_code == status.HTTP_403_FORBIDDEN
        assert delete_response.status_code == status.HTTP_403_FORBIDDEN
        invitation.refresh_from_db()
        assert invitation.role == 15

    def test_singleton_workspace_invitation_is_object_or_404(
        self,
        session_client,
    ):
        response = session_client.get("/api/users/me/workspace/invitation/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"error": "Workspace invitation not found"}

    @patch("plane.app.views.workspace.invite.track_event.delay")
    def test_individual_workspace_invite_cannot_demote_existing_admin(
        self,
        mock_track_event,
        session_client,
        workspace,
        create_user,
    ):
        invitation = WorkspaceMemberInvite.objects.create(
            workspace=workspace,
            email=create_user.email,
            token="individual-token",
            role=5,
        )

        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/invitations/{invitation.id}/join/",
            {"token": invitation.token, "accepted": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        membership = WorkspaceMember.objects.get(
            workspace=workspace,
            member=create_user,
        )
        assert membership.role == 20
        assert membership.is_active is True
        assert not WorkspaceMemberInvite.objects.filter(pk=invitation.pk).exists()
        mock_track_event.assert_called_once()

    @patch("plane.app.views.workspace.invite.track_event.delay")
    def test_singleton_workspace_invite_cannot_demote_existing_admin(
        self,
        mock_track_event,
        session_client,
        workspace,
        create_user,
    ):
        invitation = WorkspaceMemberInvite.objects.create(
            workspace=workspace,
            email=create_user.email,
            token="batch-token",
            role=5,
        )

        invitation_response = session_client.get("/api/users/me/workspace/invitation/")
        response = session_client.post("/api/users/me/workspace/invitation/")

        assert invitation_response.status_code == status.HTTP_200_OK
        assert invitation_response.json()["id"] == str(invitation.id)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        membership = WorkspaceMember.objects.get(
            workspace=workspace,
            member=create_user,
        )
        assert membership.role == 20
        assert membership.is_active is True
        assert not WorkspaceMemberInvite.objects.filter(pk=invitation.pk).exists()
        mock_track_event.assert_called_once()

        legacy_response = session_client.get("/api/users/me/workspaces/invitations/")
        assert legacy_response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_auth_invite_processing_cannot_demote_existing_admin(
        self,
        workspace,
        create_user,
    ):
        invitation = WorkspaceMemberInvite.objects.create(
            workspace=workspace,
            email=create_user.email,
            token="post-auth-token",
            role=5,
            accepted=True,
        )

        process_workspace_project_invitations(create_user)

        membership = WorkspaceMember.objects.get(
            workspace=workspace,
            member=create_user,
        )
        assert membership.role == 20
        assert membership.is_active is True
        assert not WorkspaceMemberInvite.objects.filter(pk=invitation.pk).exists()

    def test_project_invite_acceptance_preserves_workspace_admin_role(
        self,
        session_client,
        workspace,
        create_user,
    ):
        project = Project.objects.create(
            workspace=workspace,
            name="Admin invariant project",
            identifier="ADMIN",
            created_by=create_user,
        )
        invitation = ProjectMemberInvite.objects.create(
            workspace=workspace,
            project=project,
            email=create_user.email,
            token="project-token",
            role=5,
        )

        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/join/{invitation.id}/",
            {"token": invitation.token, "accepted": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        membership = WorkspaceMember.objects.get(
            workspace=workspace,
            member=create_user,
        )
        assert membership.role == 20
        assert membership.is_active is True


@pytest.mark.contract
@pytest.mark.django_db
def test_workspace_seed_bot_is_not_workspace_admin(workspace):
    task_module = "plane.bgtasks.workspace_seed_task"
    with (
        patch(f"{task_module}.create_project_and_member", return_value={}),
        patch(f"{task_module}.create_project_states", return_value={}),
        patch(f"{task_module}.create_project_labels", return_value={}),
        patch(f"{task_module}.create_cycles", return_value={}),
        patch(f"{task_module}.create_modules", return_value={}),
        patch(f"{task_module}.create_project_issues"),
        patch(f"{task_module}.create_views"),
        patch(f"{task_module}.create_pages"),
    ):
        workspace_seed.run(workspace.id)

    bot_membership = WorkspaceMember.objects.get(
        workspace=workspace,
        member__is_bot=True,
    )
    assert bot_membership.role == 15


@pytest.mark.contract
@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_kwargs",
    [
        {
            "email": "bot-admin@example.com",
            "username": "bot-admin",
            "is_bot": True,
            "is_active": True,
        },
        {
            "email": "inactive-admin@example.com",
            "username": "inactive-admin",
            "is_bot": False,
            "is_active": False,
        },
    ],
)
def test_promote_workspace_admin_command_rejects_non_human_or_inactive_user(
    workspace,
    user_kwargs,
):
    user = User.objects.create(**user_kwargs)

    with pytest.raises(CommandError, match="Only active human users"):
        call_command("promote_workspace_admin", user.email)

    assert not WorkspaceMember.objects.filter(
        workspace=workspace,
        member=user,
    ).exists()

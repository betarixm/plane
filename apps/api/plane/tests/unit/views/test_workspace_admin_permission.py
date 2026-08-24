# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from types import SimpleNamespace

import pytest

from plane.app.permissions import ProjectBasePermission
from plane.db.models import Project, ProjectMember, User, WorkspaceMember
from plane.license.api.permissions import WorkspaceAdminPermission
from plane.utils.permissions import (
    ProjectBasePermission as APIProjectBasePermission,
    WorkspaceAdminPermission as APIWorkspaceAdminPermission,
)


@pytest.mark.unit
@pytest.mark.django_db
def test_only_active_workspace_admin_has_administration_permission(workspace, create_user):
    permission = WorkspaceAdminPermission()
    admin_request = SimpleNamespace(user=create_user)
    assert permission.has_permission(admin_request, None) is True

    member = User.objects.create(
        email="member@example.com",
        username="member",
        is_active=True,
    )
    membership = WorkspaceMember.objects.create(
        workspace=workspace,
        member=member,
        role=15,
        is_active=True,
    )
    member_request = SimpleNamespace(user=member)
    assert permission.has_permission(member_request, None) is False

    membership.role = 20
    membership.is_active = False
    membership.save()
    assert permission.has_permission(member_request, None) is False


@pytest.mark.unit
@pytest.mark.django_db
def test_bot_cannot_manage_public_api_workspace_invitations(workspace, create_user, create_bot_user):
    permission = APIWorkspaceAdminPermission()
    view = SimpleNamespace(workspace_slug=workspace.slug)

    assert permission.has_permission(SimpleNamespace(user=create_user), view) is True

    WorkspaceMember.objects.create(
        workspace=workspace,
        member=create_bot_user,
        role=20,
        is_active=True,
    )

    assert permission.has_permission(SimpleNamespace(user=create_bot_user), view) is False


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.parametrize("permission_class", [ProjectBasePermission, APIProjectBasePermission])
def test_bot_workspace_admin_cannot_use_project_admin_fallback(
    permission_class,
    workspace,
    create_user,
    create_bot_user,
):
    project = Project.objects.create(
        workspace=workspace,
        name="Permission project",
        identifier="PERM",
        created_by=create_user,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=create_user,
        role=5,
        is_active=True,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=create_bot_user,
        role=20,
        is_active=True,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=create_bot_user,
        role=5,
        is_active=True,
    )
    view = SimpleNamespace(workspace_slug=workspace.slug, project_id=project.id)

    assert permission_class().has_permission(SimpleNamespace(user=create_user, method="PATCH"), view) is True
    assert permission_class().has_permission(SimpleNamespace(user=create_bot_user, method="PATCH"), view) is False


@pytest.mark.unit
def test_singleton_identity_endpoints_read_from_primary():
    from plane.app.views import (
        UserWorkspaceAdminEndpoint,
        UserWorkspaceEndpoint,
        UserWorkspaceInvitationEndpoint,
        WorkspaceJoinEndpoint,
    )

    assert UserWorkspaceAdminEndpoint.use_read_replica is False
    assert UserWorkspaceEndpoint.use_read_replica is False
    assert UserWorkspaceInvitationEndpoint.use_read_replica is False
    assert WorkspaceJoinEndpoint.use_read_replica is False

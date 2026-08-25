# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from types import SimpleNamespace

import pytest

from plane.app.permissions import ProjectBasePermission
from plane.db.models import Project, ProjectMember, User, WorkspaceMember
from plane.utils.permissions import (
    ProjectBasePermission as APIProjectBasePermission,
    WorkspaceAdminPermission as APIWorkspaceAdminPermission,
)


@pytest.mark.unit
@pytest.mark.django_db
def test_workspace_admin_permission_requires_an_active_external_admin(
    workspace,
    create_user,
    external_identity_source,
):
    permission = APIWorkspaceAdminPermission()
    view = SimpleNamespace(workspace_slug=workspace.slug)

    assert permission.has_permission(SimpleNamespace(user=create_user), view) is True

    local_only_admin = User.objects.create(
        email="local-only-admin@example.com",
        username="local-only-admin",
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=local_only_admin,
        role=20,
        is_active=True,
    )

    assert permission.has_permission(SimpleNamespace(user=local_only_admin), view) is False


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.parametrize("permission_class", [ProjectBasePermission, APIProjectBasePermission])
def test_workspace_admin_project_fallback_requires_external_identity(
    permission_class,
    workspace,
    create_user,
    external_identity_source,
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

    local_only_admin = User.objects.create(
        email="local-only-project-admin@example.com",
        username="local-only-project-admin",
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=local_only_admin,
        role=20,
        is_active=True,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=local_only_admin,
        role=5,
        is_active=True,
    )
    view = SimpleNamespace(workspace_slug=workspace.slug, project_id=project.id)

    assert permission_class().has_permission(
        SimpleNamespace(user=create_user, method="PATCH"),
        view,
    ) is True
    assert permission_class().has_permission(
        SimpleNamespace(user=local_only_admin, method="PATCH"),
        view,
    ) is False


@pytest.mark.unit
def test_singleton_workspace_endpoint_reads_from_primary():
    from plane.app.views import UserWorkspaceEndpoint

    assert UserWorkspaceEndpoint.use_read_replica is False

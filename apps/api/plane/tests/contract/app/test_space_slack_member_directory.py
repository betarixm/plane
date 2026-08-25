# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest
from rest_framework import status

from plane.db.models import DeployBoard, Project, ProjectMember, User, WorkspaceMember


pytestmark = [pytest.mark.contract, pytest.mark.django_db]


def test_public_project_member_directory_excludes_stale_external_identity(
    api_client,
    workspace,
    create_user,
    external_identity_source,
    bind_external_identity,
):
    project = Project.objects.create(
        name="Public roster",
        identifier="PR",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=create_user,
        role=20,
        is_active=True,
    )
    deploy_board = DeployBoard.objects.create(
        workspace=workspace,
        project=project,
        entity_identifier=project.id,
        entity_name="project",
    )

    stale_user = User.objects.create(
        email=f"stale-{uuid4().hex}@example.com",
        username=f"stale-{uuid4().hex}",
        display_name="Stale Slack member",
        is_active=True,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=stale_user,
        role=15,
        is_active=True,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=stale_user,
        role=15,
        is_active=True,
    )
    stale_identity = bind_external_identity(stale_user)
    stale_identity.source_generation = external_identity_source.source.generation + 1
    stale_identity.save(update_fields=["source_generation", "updated_at"])

    response = api_client.get(f"/api/public/anchor/{deploy_board.anchor}/members/")

    assert response.status_code == status.HTTP_200_OK
    returned_member_ids = {str(item["member"]) for item in response.data}
    assert str(create_user.id) in returned_member_ids
    assert str(stale_user.id) not in returned_member_ids

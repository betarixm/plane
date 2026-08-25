# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest
from rest_framework import status

from plane.db.models import (
    Project,
    ProjectMember,
    User,
    UserRecentVisit,
    WorkspaceMember,
)


pytestmark = [pytest.mark.contract, pytest.mark.django_db]


def test_project_and_recent_visit_member_projections_exclude_stale_slack_generation(
    session_client,
    workspace,
    create_user,
    external_identity_source,
    bind_external_identity,
):
    project = Project.objects.create(
        name="Current external roster",
        identifier=f"CSR{uuid4().hex[:4].upper()}",
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
    stale_identity.source_generation = (
        external_identity_source.source.generation + 1
    )
    stale_identity.save(update_fields=["source_generation", "updated_at"])
    UserRecentVisit.objects.create(
        workspace=workspace,
        user=create_user,
        entity_name="project",
        entity_identifier=project.id,
    )

    project_response = session_client.get(
        "/api/workspace/projects/details/"
    )
    recent_response = session_client.get(
        "/api/workspace/recent-visits/",
        {"entity_name": "project"},
    )

    assert project_response.status_code == status.HTTP_200_OK
    project_data = next(
        item for item in project_response.json() if item["id"] == str(project.id)
    )
    assert set(project_data["members"]) == {str(create_user.id)}

    assert recent_response.status_code == status.HTTP_200_OK
    recent_data = next(
        item
        for item in recent_response.json()
        if item["entity_identifier"] == str(project.id)
    )
    assert set(recent_data["entity_data"]["project_members"]) == {
        str(create_user.id)
    }

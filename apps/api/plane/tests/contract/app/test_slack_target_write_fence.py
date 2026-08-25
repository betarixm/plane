# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.app.serializers.issue import IssueCreateSerializer
from plane.db.models import (
    Issue,
    IssueAssignee,
    Project,
    ProjectMember,
    ExternalIdentity,
    User,
    WorkspaceMember,
)
from plane.utils import identity_access


pytestmark = [pytest.mark.contract, pytest.mark.django_db]


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(
        workspace=workspace,
        name="Slack fence",
        identifier="SLF",
        created_by=create_user,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=create_user,
        role=20,
    )
    return project


def test_issue_target_is_rechecked_after_source_lock_and_before_save(
    session_client,
    workspace,
    project,
    external_identity_source,
    monkeypatch,
):
    target = User.objects.create(
        email="target@example.com",
        username="slack-target",
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=target,
        role=15,
    )
    target_identity = ExternalIdentity.objects.create(
        user=target,
        source=external_identity_source.source,
        external_user_id="UTARGET",
        source_generation=external_identity_source.source.generation,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=target,
        role=15,
    )

    events = []
    original_lock = identity_access.lock_active_identity_source
    original_is_valid = IssueCreateSerializer.is_valid
    original_save = IssueCreateSerializer.save

    def lock_then_remove_target(*, workspace_id):
        source = original_lock(workspace_id=workspace_id)
        events.append("source-lock")
        target_identity.is_active = False
        target_identity.save(update_fields=["is_active", "updated_at"])
        return source

    def tracked_is_valid(serializer, *args, **kwargs):
        events.append("target-validation")
        return original_is_valid(serializer, *args, **kwargs)

    def tracked_save(serializer, *args, **kwargs):
        events.append("save")
        return original_save(serializer, *args, **kwargs)

    monkeypatch.setattr(
        identity_access,
        "lock_active_identity_source",
        lock_then_remove_target,
    )
    monkeypatch.setattr(IssueCreateSerializer, "is_valid", tracked_is_valid)
    monkeypatch.setattr(IssueCreateSerializer, "save", tracked_save)
    monkeypatch.setattr(
        "plane.app.views.issue.base.issue_activity.delay",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "plane.app.views.issue.base.model_activity.delay",
        lambda **kwargs: None,
    )

    response = session_client.post(
        f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/",
        {"name": "Linearized issue", "assignee_ids": [str(target.id)]},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    issue = Issue.objects.get(name="Linearized issue")
    assert not IssueAssignee.objects.filter(issue=issue, assignee=target).exists()
    assert events[:3] == ["source-lock", "target-validation", "save"]

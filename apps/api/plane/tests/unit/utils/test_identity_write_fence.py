# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.core.exceptions import PermissionDenied

from plane.utils import identity_access


pytestmark = pytest.mark.unit


def test_project_write_fence_is_source_first_and_covers_save(monkeypatch):
    events = []

    @contextmanager
    def tracked_atomic():
        events.append("transaction-enter")
        try:
            yield
        finally:
            events.append("transaction-exit")

    def lock_source(*, workspace_id):
        events.append("source-lock")
        return SimpleNamespace(workspace_id=workspace_id)

    def lock_workspace_member(*, workspace_id, user_id):
        events.append("workspace-member-lock")
        return SimpleNamespace(
            workspace_id=workspace_id,
            member_id=user_id,
            role=20,
        )

    project_members = MagicMock()
    project_members.select_for_update.return_value.filter.return_value.only.return_value.first.side_effect = (
        lambda: events.append("project-member-lock") or SimpleNamespace(role=20)
    )
    projects = MagicMock()
    projects.filter.return_value.exists.return_value = True

    monkeypatch.setattr(identity_access.transaction, "atomic", tracked_atomic)
    monkeypatch.setattr(
        identity_access,
        "lock_active_identity_source",
        lock_source,
    )
    monkeypatch.setattr(
        identity_access,
        "lock_active_workspace_member",
        lock_workspace_member,
    )
    monkeypatch.setattr(
        identity_access,
        "active_project_members",
        lambda: project_members,
    )
    monkeypatch.setattr(
        identity_access.Project.objects,
        "using",
        lambda alias: projects,
    )

    with identity_access.identity_project_write_fence(
        workspace_id="workspace-id",
        project_id="project-id",
        user_id="user-id",
        allowed_roles=[20],
    ):
        events.extend(["target-validation", "save"])

    assert events == [
        "transaction-enter",
        "source-lock",
        "workspace-member-lock",
        "project-member-lock",
        "target-validation",
        "save",
        "transaction-exit",
    ]


def test_background_task_is_not_published_until_commit(monkeypatch):
    callbacks = []
    task = MagicMock()

    def capture_on_commit(callback, *, robust):
        callbacks.append(callback)
        assert robust is True

    monkeypatch.setattr(
        identity_access.transaction,
        "on_commit",
        capture_on_commit,
    )

    identity_access.enqueue_task_after_commit(
        task,
        "positional",
        keyword="value",
    )

    task.delay.assert_not_called()
    assert len(callbacks) == 1

    callbacks[0]()

    task.delay.assert_called_once_with("positional", keyword="value")


def test_missing_active_source_is_normalized_to_permission_denied(
    monkeypatch,
):
    @contextmanager
    def atomic():
        yield

    def missing_source(*, workspace_id):
        raise identity_access.IdentitySource.DoesNotExist

    monkeypatch.setattr(identity_access.transaction, "atomic", atomic)
    monkeypatch.setattr(
        identity_access,
        "lock_active_identity_source",
        missing_source,
    )

    with pytest.raises(PermissionDenied, match="active external identity source"):
        with identity_access.identity_workspace_write_fence(
            workspace_id="workspace-id",
            user_id="user-id",
        ):
            raise AssertionError("the fenced mutation must not run")

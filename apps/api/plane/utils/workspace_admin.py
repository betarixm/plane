# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from contextlib import contextmanager

from django.db import transaction

from plane.db.models import Workspace, WorkspaceMember

WORKSPACE_ADMIN_ROLE = 20


class LastWorkspaceAdminError(Exception):
    """Raised when a membership mutation would leave no human administrator."""


def active_human_workspace_admins():
    """Return active human administrators of the active singleton workspace."""

    return WorkspaceMember.objects.filter(
        role=WORKSPACE_ADMIN_ROLE,
        is_active=True,
        workspace__deleted_at__isnull=True,
        member__is_active=True,
        member__is_bot=False,
    )


def is_workspace_admin(user):
    """Return whether a user holds unified workspace/instance authority."""

    if not user or not user.is_authenticated:
        return False
    return active_human_workspace_admins().filter(member=user).exists()


def activate_invited_workspace_member(*, workspace, user, role, created_by=None):
    """Activate an invitee without silently demoting an active human admin.

    Callers must hold ``workspace_admin_guard`` so the membership lock follows
    the common workspace-first lock order.
    """

    workspace_member = WorkspaceMember.objects.select_for_update().filter(workspace=workspace, member=user).first()
    if workspace_member is None:
        return WorkspaceMember.objects.create(
            workspace=workspace,
            member=user,
            role=role,
            created_by=created_by,
        )

    preserve_admin_role = (
        workspace_member.is_active
        and workspace_member.role == WORKSPACE_ADMIN_ROLE
        and user.is_active
        and not user.is_bot
    )
    workspace_member.is_active = True
    if not preserve_admin_role:
        workspace_member.role = role
    workspace_member.save(update_fields=["is_active", "role", "updated_at"])
    return workspace_member


@contextmanager
def workspace_admin_guard(*, workspace_id=None, slug=None):
    """Serialize admin-depleting mutations and enforce a human admin remains.

    Every API path that can lower an administrator's role or deactivate their
    membership must use this guard. Locking the workspace row gives those
    otherwise independent membership rows one shared serialization point.
    """

    if (workspace_id is None) == (slug is None):
        raise ValueError("Provide exactly one of workspace_id or slug")

    lookup = {"pk": workspace_id} if workspace_id is not None else {"slug": slug}
    with transaction.atomic():
        workspace = Workspace.objects.select_for_update().get(
            deleted_at__isnull=True,
            **lookup,
        )
        yield workspace
        if not active_human_workspace_admins().filter(workspace=workspace).exists():
            raise LastWorkspaceAdminError("The workspace must retain at least one active human administrator")

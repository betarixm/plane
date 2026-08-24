# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import transaction
from django.utils import timezone

from plane.bgtasks.event_tracking_task import track_event

# Module imports
from plane.db.models import (
    ProjectMember,
    ProjectMemberInvite,
    WorkspaceMember,
    WorkspaceMemberInvite,
)
from plane.utils.analytics_events import USER_JOINED_WORKSPACE
from plane.utils.cache import invalidate_cache_directly
from plane.utils.workspace_admin import (
    activate_invited_workspace_member,
    workspace_admin_guard,
)


def _notify_workspace_join(*, user_id, workspace_id, workspace_slug, role):
    invalidate_cache_directly(
        path=f"/api/workspaces/{workspace_slug}/members/",
        url_params=False,
        user=False,
        multiple=True,
    )
    track_event.delay(
        user_id=user_id,
        event_name=USER_JOINED_WORKSPACE,
        slug=workspace_slug,
        event_properties={
            "user_id": user_id,
            "workspace_id": workspace_id,
            "workspace_slug": workspace_slug,
            "role": role,
            "joined_at": str(timezone.now().isoformat()),
        },
    )


def process_workspace_project_invitations(user):
    """Apply accepted invitations using the workspace admin lock protocol."""

    workspace_invites = list(
        WorkspaceMemberInvite.objects.filter(email=user.email, accepted=True)
        .select_related("workspace")
        .order_by("created_at")
    )
    for invitation in workspace_invites:
        with workspace_admin_guard(workspace_id=invitation.workspace_id) as workspace:
            locked_invitation = WorkspaceMemberInvite.objects.select_for_update().get(
                pk=invitation.pk,
                workspace=workspace,
            )
            workspace_member = activate_invited_workspace_member(
                workspace=workspace,
                user=user,
                role=locked_invitation.role,
            )
            locked_invitation.delete()
            transaction.on_commit(
                lambda user_id=user.id,
                workspace_id=workspace.id,
                workspace_slug=workspace.slug,
                role=workspace_member.role: _notify_workspace_join(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    workspace_slug=workspace_slug,
                    role=role,
                )
            )

    project_invites = list(
        ProjectMemberInvite.objects.filter(email=user.email, accepted=True)
        .select_related("workspace", "project")
        .order_by("created_at")
    )
    for invitation in project_invites:
        with workspace_admin_guard(workspace_id=invitation.workspace_id) as workspace:
            locked_invitation = ProjectMemberInvite.objects.select_for_update().get(
                pk=invitation.pk,
                workspace=workspace,
            )
            workspace_role = locked_invitation.role if locked_invitation.role in [5, 15] else 15
            workspace_member = (
                WorkspaceMember.objects.select_for_update().filter(workspace=workspace, member=user).first()
            )
            if workspace_member is None:
                WorkspaceMember.objects.create(
                    workspace=workspace,
                    role=workspace_role,
                    member=user,
                    created_by_id=locked_invitation.created_by_id,
                )
            elif not workspace_member.is_active:
                workspace_member.is_active = True
                workspace_member.save(update_fields=["is_active", "updated_at"])

            ProjectMember.objects.get_or_create(
                workspace=workspace,
                project_id=locked_invitation.project_id,
                member=user,
                defaults={
                    "role": workspace_role,
                    "created_by_id": locked_invitation.created_by_id,
                },
            )
            locked_invitation.delete()

# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.db.models import Profile, Workspace, WorkspaceMemberInvite


def get_redirection_path(user):
    # Handle redirections
    profile, _ = Profile.objects.get_or_create(user=user)

    # Redirect to onboarding if the user is not onboarded yet
    if not profile.is_onboarded:
        return "onboarding"

    workspace = Workspace.objects.filter(workspace_member__member_id=user.id, workspace_member__is_active=True).first()
    if workspace:
        return workspace.slug

    # Redirect to invitations if the user has unaccepted invitations
    if WorkspaceMemberInvite.objects.filter(email=user.email).count():
        return "invitations"

    # There is no user-created workspace path in a singleton deployment.
    # Users without membership wait for an invitation instead.
    return "invitations"

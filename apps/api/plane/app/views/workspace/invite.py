# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from datetime import datetime

import jwt

# Django imports
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone

# Third party modules
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WorkspaceAdminPermission
from plane.app.serializers import (
    WorkSpaceMemberInvitePublicSerializer,
    WorkSpaceMemberInviteSerializer,
    WorkSpaceMemberSerializer,
)
from plane.app.views.base import BaseAPIView
from plane.bgtasks.event_tracking_task import track_event
from plane.bgtasks.workspace_invitation_task import workspace_invitation
from plane.db.models import Workspace, WorkspaceMember, WorkspaceMemberInvite
from plane.utils.analytics_events import USER_INVITED_TO_WORKSPACE, USER_JOINED_WORKSPACE
from plane.utils.cache import invalidate_cache, invalidate_cache_directly
from plane.utils.host import base_host
from plane.utils.workspace_admin import (
    LastWorkspaceAdminError,
    activate_invited_workspace_member,
    workspace_admin_guard,
)

from .. import BaseViewSet


class WorkspaceInvitationsViewset(BaseViewSet):
    """Endpoint for creating, listing and  deleting workspaces"""

    serializer_class = WorkSpaceMemberInviteSerializer
    model = WorkspaceMemberInvite

    permission_classes = [WorkspaceAdminPermission]

    def get_queryset(self):
        return self.filter_queryset(
            super()
            .get_queryset()
            .filter(workspace__slug=self.kwargs.get("slug"))
            .select_related("workspace", "workspace__owner", "created_by")
        )

    def create(self, request, slug):
        emails = request.data.get("emails", [])
        # Check if email is provided
        if not emails:
            return Response({"error": "Emails are required"}, status=status.HTTP_400_BAD_REQUEST)

        # check for role level of the requesting user
        requesting_user = WorkspaceMember.objects.get(workspace__slug=slug, member=request.user, is_active=True)

        # Check if any invited user has an higher role
        if len([email for email in emails if int(email.get("role", 5)) > requesting_user.role]):
            return Response(
                {"error": "You cannot invite a user with higher role"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the workspace object
        workspace = Workspace.objects.get(slug=slug)

        # Check if user is already a member of workspace
        workspace_members = WorkspaceMember.objects.filter(
            workspace_id=workspace.id,
            member__email__in=[email.get("email") for email in emails],
            is_active=True,
        ).select_related("member", "member__avatar_asset")

        if workspace_members:
            return Response(
                {
                    "error": "Some users are already member of workspace",
                    "workspace_users": WorkSpaceMemberSerializer(workspace_members, many=True).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        workspace_invitations = []
        for email in emails:
            try:
                validate_email(email.get("email"))
                workspace_invitations.append(
                    WorkspaceMemberInvite(
                        email=email.get("email").strip().lower(),
                        workspace_id=workspace.id,
                        token=jwt.encode(
                            {"email": email, "timestamp": datetime.now().timestamp()},
                            settings.SECRET_KEY,
                            algorithm="HS256",
                        ),
                        role=email.get("role", 5),
                        created_by=request.user,
                    )
                )
            except ValidationError:
                return Response(
                    {
                        "error": f"Invalid email - {email} provided a valid email address is required to send the invite"  # noqa: E501
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        # Create workspace member invite
        workspace_invitations = WorkspaceMemberInvite.objects.bulk_create(
            workspace_invitations, batch_size=10, ignore_conflicts=True
        )

        current_site = base_host(request=request, is_app=True)

        # Send invitations
        for invitation in workspace_invitations:
            workspace_invitation.delay(
                invitation.email,
                workspace.id,
                invitation.token,
                current_site,
                request.user.email,
            )
            track_event.delay(
                user_id=request.user.id,
                event_name=USER_INVITED_TO_WORKSPACE,
                slug=slug,
                event_properties={
                    "user_id": request.user.id,
                    "workspace_id": workspace.id,
                    "workspace_slug": workspace.slug,
                    "invitee_role": invitation.role,
                    "invited_at": str(timezone.now()),
                    "invitee_email": invitation.email,
                },
            )

        return Response({"message": "Emails sent successfully"}, status=status.HTTP_200_OK)

    def destroy(self, request, slug, pk):
        workspace_member_invite = WorkspaceMemberInvite.objects.get(pk=pk, workspace__slug=slug)
        workspace_member_invite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceJoinEndpoint(BaseAPIView):
    permission_classes = [AllowAny]
    use_read_replica = False
    """Invitation response endpoint the user can respond to the invitation"""

    @invalidate_cache(path="/api/instances/workspace/", user=False)
    @invalidate_cache(path="/api/users/me/workspace/", multiple=True)
    @invalidate_cache(
        path="/api/workspaces/:slug/members/",
        user=False,
        multiple=True,
        url_params=True,
    )
    @invalidate_cache(path="/api/users/me/settings/", multiple=True)
    def post(self, request, slug, pk):
        workspace_invite = WorkspaceMemberInvite.objects.get(pk=pk, workspace__slug=slug)

        token = request.data.get("token", "")

        # Validate the token to verify the user received the invitation email
        if not token or workspace_invite.token != token:
            return Response(
                {"error": "You do not have permission to join the workspace"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Require an authenticated session — the accepting user must be the
        # person who was invited.  Without this check an attacker who registers
        # with the invited address (email-squat) and obtains the token via the
        # GET endpoint can steal the workspace membership (GHSA-4vj8-p63v-8p24).
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required to accept workspace invitation"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if request.user.email.lower() != workspace_invite.email.lower():
            return Response(
                {"error": "You do not have permission to accept this invitation"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            with workspace_admin_guard(workspace_id=workspace_invite.workspace_id) as workspace:
                workspace_invite = (
                    WorkspaceMemberInvite.objects.select_for_update()
                    .select_related("workspace")
                    .get(pk=pk, workspace=workspace)
                )
                if workspace_invite.responded_at is not None:
                    return Response(
                        {"error": "You have already responded to the invitation request"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                workspace_invite.accepted = request.data.get("accepted", False)
                workspace_invite.responded_at = timezone.now()
                workspace_invite.save(update_fields=["accepted", "responded_at", "updated_at"])

                if not workspace_invite.accepted:
                    return Response(
                        {"message": "Workspace Invitation was not accepted"},
                        status=status.HTTP_200_OK,
                    )

                workspace_member = activate_invited_workspace_member(
                    workspace=workspace,
                    user=request.user,
                    role=workspace_invite.role,
                )
                workspace_invite.delete()

            track_event.delay(
                user_id=request.user.id,
                event_name=USER_JOINED_WORKSPACE,
                slug=slug,
                event_properties={
                    "user_id": request.user.id,
                    "workspace_id": workspace.id,
                    "workspace_slug": workspace.slug,
                    "role": workspace_member.role,
                    "joined_at": str(timezone.now()),
                },
            )
            return Response(
                {"message": "Workspace Invitation Accepted"},
                status=status.HTTP_200_OK,
            )
        except LastWorkspaceAdminError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, slug, pk):
        workspace_invitation = WorkspaceMemberInvite.objects.get(workspace__slug=slug, pk=pk)
        # Use the public serializer that omits the token and invite_link fields so
        # that an unauthenticated caller cannot retrieve the acceptance token
        # (GHSA-86mg-259g-pwgg / GHSA-gf48-p6jp-cwc4).
        serializer = WorkSpaceMemberInvitePublicSerializer(workspace_invitation)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserWorkspaceInvitationEndpoint(BaseAPIView):
    """Return or accept the current user's invitation to the singleton workspace."""

    use_read_replica = False

    def get(self, request):
        invitation = (
            WorkspaceMemberInvite.objects.filter(
                email__iexact=request.user.email,
                responded_at__isnull=True,
            )
            .select_related("workspace")
            .first()
        )
        if invitation is None:
            return Response(
                {"error": "Workspace invitation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            WorkSpaceMemberInvitePublicSerializer(invitation).data,
            status=status.HTTP_200_OK,
        )

    @invalidate_cache(path="/api/instances/workspace/", user=False)
    @invalidate_cache(path="/api/users/me/workspace/", multiple=True)
    def post(self, request):
        workspace = Workspace.objects.first()
        if workspace is None:
            return Response(
                {"error": "Workspace is not configured yet"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            with workspace_admin_guard(workspace_id=workspace.id) as workspace:
                invitation = (
                    WorkspaceMemberInvite.objects.select_for_update()
                    .filter(
                        workspace=workspace,
                        email__iexact=request.user.email,
                        responded_at__isnull=True,
                    )
                    .first()
                )
                if invitation is None:
                    return Response(
                        {"error": "Workspace invitation not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                workspace_member = activate_invited_workspace_member(
                    workspace=workspace,
                    user=request.user,
                    role=invitation.role,
                    created_by=request.user,
                )
                invitation.delete()
        except LastWorkspaceAdminError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        invalidate_cache_directly(
            path=f"/api/workspaces/{workspace.slug}/members/",
            user=False,
            request=request,
            multiple=True,
        )
        track_event.delay(
            user_id=request.user.id,
            event_name=USER_JOINED_WORKSPACE,
            slug=workspace.slug,
            event_properties={
                "user_id": request.user.id,
                "workspace_id": workspace.id,
                "workspace_slug": workspace.slug,
                "role": workspace_member.role,
                "joined_at": str(timezone.now()),
            },
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.db.models import (
    Project,
    ProjectMember,
    ProjectUserProperty,
    Workspace,
)
from plane.db.models.project import ProjectNetwork
from plane.utils.identity_access import (
    active_workspace_members,
    lock_active_identity_source,
)

from .base import BaseViewSet


class UserProjectJoinViewSet(BaseViewSet):
    """Let an active externally projected member join visible local projects."""

    model = ProjectMember

    @transaction.atomic
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def create(self, request, slug):
        project_ids = request.data.get("project_ids", [])
        if not isinstance(project_ids, list):
            return Response(
                {"error": "project_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workspace = Workspace.objects.using("default").get(slug=slug)
        lock_active_identity_source(workspace_id=workspace.id)
        workspace_member = active_workspace_members().select_for_update().get(
            workspace=workspace,
            member=request.user,
        )
        if workspace_member.role not in {ROLE.ADMIN.value, ROLE.MEMBER.value}:
            return Response(
                {"error": "You don't have the required permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        projects = list(
            Project.objects.using("default").filter(
                id__in=project_ids,
                workspace=workspace,
            ).only("id", "network")
        )
        if any(
            project.network == ProjectNetwork.SECRET.value
            and workspace_member.role != ROLE.ADMIN.value
            for project in projects
        ):
            return Response(
                {"error": "Only workspace admins can join private projects"},
                status=status.HTTP_403_FORBIDDEN,
            )

        validated_project_ids = [str(project.id) for project in projects]
        existing_memberships = ProjectMember.objects.select_for_update().filter(
            workspace=workspace_member.workspace,
            project_id__in=validated_project_ids,
            member=request.user,
        )
        if workspace_member.role in {ROLE.ADMIN.value, ROLE.GUEST.value}:
            existing_memberships.update(
                is_active=True,
                role=workspace_member.role,
            )
        else:
            existing_memberships.update(is_active=True)

        ProjectMember.objects.bulk_create(
            [
                ProjectMember(
                    project_id=project_id,
                    member=request.user,
                    role=workspace_member.role,
                    workspace=workspace_member.workspace,
                    created_by=request.user,
                )
                for project_id in validated_project_ids
            ],
            ignore_conflicts=True,
        )
        ProjectUserProperty.objects.bulk_create(
            [
                ProjectUserProperty(
                    project_id=project_id,
                    user=request.user,
                    workspace=workspace_member.workspace,
                    created_by=request.user,
                )
                for project_id in validated_project_ids
            ],
            ignore_conflicts=True,
        )

        return Response(
            {"message": "Projects joined successfully"},
            status=status.HTTP_201_CREATED,
        )

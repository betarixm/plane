# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from django.db.models import Count, OuterRef
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.views.base import BaseAPIView
from plane.db.models import Project, Workspace, WorkspaceMember
from plane.license.api.permissions import WorkspaceAdminPermission
from plane.license.api.serializers import WorkspaceSerializer


class InstanceWorkspaceEndpoint(BaseAPIView):
    model = Workspace
    serializer_class = WorkspaceSerializer
    permission_classes = [WorkspaceAdminPermission]

    def get(self, request):
        project_count = (
            Project.objects.filter(workspace_id=OuterRef("id"))
            .order_by()
            .values("workspace_id")
            .annotate(count=Count("id"))
            .values("count")
        )

        member_count = (
            WorkspaceMember.objects.filter(workspace=OuterRef("id"), member__is_bot=False, is_active=True)
            .order_by()
            .values("workspace_id")
            .annotate(count=Count("id"))
            .values("count")
        )

        workspace = Workspace.objects.annotate(
            total_projects=project_count,
            total_members=member_count,
        ).first()
        if workspace is None:
            return Response(
                {"error": "Workspace is not configured yet"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(WorkspaceSerializer(workspace).data, status=status.HTTP_200_OK)

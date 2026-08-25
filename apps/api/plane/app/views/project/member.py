# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from uuid import UUID

from django.db import transaction
from django.db.models import Min
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import WorkspaceUserPermission
from plane.app.permissions.base import ROLE, allow_permission
from plane.app.serializers import (
    ProjectMemberAdminSerializer,
    ProjectMemberPreferenceSerializer,
    ProjectMemberRoleSerializer,
    ProjectMemberSerializer,
)
from plane.db.models import Project, ProjectMember, ProjectUserProperty
from plane.utils.identity_access import (
    active_workspace_members,
    lock_active_identity_source,
    lock_active_workspace_member,
    project_role_for_workspace_role,
)

# Module imports
from .base import BaseAPIView, BaseViewSet


class ProjectMemberViewSet(BaseViewSet):
    serializer_class = ProjectMemberAdminSerializer
    model = ProjectMember

    search_fields = ["member__display_name", "member__first_name"]

    def get_queryset(self):
        active_member_ids = (
            active_workspace_members()
            .filter(
                workspace__slug=self.kwargs.get("slug"),
            )
            .values("member_id")
        )
        return self.filter_queryset(
            super()
            .get_queryset()
            .filter(workspace__slug=self.kwargs.get("slug"))
            .filter(project_id=self.kwargs.get("project_id"))
            .filter(member_id__in=active_member_ids)
            .select_related("project")
            .select_related("member")
            .select_related("workspace")
        )

    @transaction.atomic
    @allow_permission([ROLE.ADMIN])
    def create(self, request, slug, project_id):
        members = request.data.get("members", [])
        project = Project.objects.using("default").get(pk=project_id, workspace__slug=slug)
        lock_active_identity_source(workspace_id=project.workspace_id)
        requester_workspace_member = lock_active_workspace_member(
            workspace_id=project.workspace_id,
            user_id=request.user.id,
        )
        if requester_workspace_member is None:
            return Response(
                {"error": "An active external workspace membership is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        requester_is_admin = (
            ProjectMember.objects.select_for_update()
            .filter(
                project=project,
                member=request.user,
                is_active=True,
            )
            .filter(
                role=ROLE.ADMIN.value,
            )
            .exists()
            or requester_workspace_member.role == ROLE.ADMIN.value
        )
        if not requester_is_admin:
            return Response(
                {"error": "You don't have the required permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not isinstance(members, list) or not members:
            return Response(
                {"error": "At least one member is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member_roles: dict[str, int] = {}
        for member_payload in members:
            try:
                member_id = str(UUID(str(member_payload["member_id"])))
                requested_role = int(member_payload.get("role", ROLE.GUEST.value))
            except (KeyError, TypeError, ValueError):
                return Response(
                    {"error": "Each member must have a valid member_id and role"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            workspace_member = (
                active_workspace_members()
                .select_for_update()
                .filter(
                    workspace=project.workspace,
                    member_id=member_id,
                )
                .only("role")
                .first()
            )
            if workspace_member is None:
                return Response(
                    {"error": "Every project member must be an active member of the connected external workspace"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                effective_role = project_role_for_workspace_role(
                    workspace_role=workspace_member.role,
                    requested_role=requested_role,
                )
            except ValueError:
                return Response(
                    {"error": "Invalid project role"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if effective_role != requested_role:
                return Response(
                    {"error": "The project role must respect the member's external workspace role"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            member_roles[member_id] = effective_role

        existing_project_members = list(
            ProjectMember.objects.select_for_update().filter(
                project=project,
                member_id__in=member_roles,
            )
        )
        active_admin_member_ids = {
            str(member_id)
            for member_id in ProjectMember.objects.select_for_update()
            .filter(
                project=project,
                role=ROLE.ADMIN.value,
                is_active=True,
            )
            .values_list("member_id", flat=True)
        }
        resulting_admin_member_ids = {
            member_id
            for member_id in active_admin_member_ids
            if member_id not in member_roles or member_roles[member_id] == ROLE.ADMIN.value
        }
        resulting_admin_member_ids.update(
            member_id for member_id, role in member_roles.items() if role == ROLE.ADMIN.value
        )
        if not resulting_admin_member_ids:
            return Response(
                {"error": "The project must retain at least one active administrator"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing_member_ids = {str(project_member.member_id) for project_member in existing_project_members}
        for project_member in existing_project_members:
            project_member.role = member_roles[str(project_member.member_id)]
            project_member.is_active = True
        ProjectMember.objects.bulk_update(
            existing_project_members,
            ["is_active", "role"],
            batch_size=100,
        )

        member_sort_orders = (
            ProjectUserProperty.objects.filter(
                workspace=project.workspace,
                user_id__in=member_roles,
            )
            .values("user_id")
            .annotate(min_sort_order=Min("sort_order"))
        )
        sort_order_map = {str(item["user_id"]): item["min_sort_order"] for item in member_sort_orders}
        ProjectMember.objects.bulk_create(
            [
                ProjectMember(
                    member_id=member_id,
                    role=role,
                    project=project,
                    workspace=project.workspace,
                )
                for member_id, role in member_roles.items()
                if member_id not in existing_member_ids
            ],
            batch_size=10,
            ignore_conflicts=True,
        )
        ProjectUserProperty.objects.bulk_create(
            [
                ProjectUserProperty(
                    user_id=member_id,
                    project=project,
                    workspace=project.workspace,
                    sort_order=(
                        sort_order_map[member_id] - 10000 if sort_order_map.get(member_id) is not None else 65535
                    ),
                )
                for member_id in member_roles
            ],
            batch_size=10,
            ignore_conflicts=True,
        )

        project_members = ProjectMember.objects.filter(
            project_id=project_id,
            member_id__in=member_roles,
        )
        # Serialize the project members
        serializer = ProjectMemberRoleSerializer(project_members, many=True)
        # Return the serialized data
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def list(self, request, slug, project_id):
        # Get the list of project members for the project
        active_member_ids = (
            active_workspace_members()
            .filter(
                workspace__slug=slug,
            )
            .values("member_id")
        )
        project_members = ProjectMember.objects.filter(
            project_id=project_id,
            workspace__slug=slug,
            is_active=True,
            member_id__in=active_member_ids,
        ).select_related("project", "member", "workspace")

        serializer = ProjectMemberRoleSerializer(project_members, fields=("id", "member", "role"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def retrieve(self, request, slug, project_id, pk):
        active_member_ids = (
            active_workspace_members()
            .filter(
                workspace__slug=slug,
            )
            .values("member_id")
        )
        requesting_project_member = ProjectMember.objects.get(
            project_id=project_id,
            workspace__slug=slug,
            member=request.user,
            is_active=True,
            member_id__in=active_member_ids,
        )

        project_member = (
            ProjectMember.objects.filter(
                pk=pk,
                project_id=project_id,
                workspace__slug=slug,
                is_active=True,
                member_id__in=active_member_ids,
            )
            .select_related("project", "member", "workspace")
            .first()
        )

        if not project_member:
            return Response(
                {"error": "Project member not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if requesting_project_member.role > ROLE.GUEST.value:
            serializer = ProjectMemberAdminSerializer(project_member)
        else:
            serializer = ProjectMemberRoleSerializer(project_member, fields=("id", "member", "role"))

        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def partial_update(self, request, slug, project_id, pk):
        unsupported_fields = set(request.data) - {"role", "is_active"}
        if unsupported_fields:
            return Response(
                {"error": "Only role and is_active can be updated"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project = (
            Project.objects.using("default")
            .only("workspace_id")
            .get(
                pk=project_id,
                workspace__slug=slug,
            )
        )
        lock_active_identity_source(workspace_id=project.workspace_id)
        requester_workspace_member = lock_active_workspace_member(
            workspace_id=project.workspace_id,
            user_id=request.user.id,
        )
        if requester_workspace_member is None:
            return Response(
                {"error": "An active external workspace membership is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        project_member = ProjectMember.objects.select_for_update().get(
            pk=pk,
            project=project,
            is_active=True,
        )

        # Fetch the target's workspace role (used to cap the new project role)
        target_workspace_role = (
            active_workspace_members()
            .select_for_update()
            .get(
                workspace_id=project_member.workspace_id,
                member=project_member.member,
            )
            .role
        )
        # Fetch the requester's workspace role to decide if they may bypass project-role checks
        is_workspace_admin = requester_workspace_member.role == ROLE.ADMIN.value

        # Check if the user is not editing their own role if they are not an admin
        if request.user.id == project_member.member_id and not is_workspace_admin:
            return Response(
                {"error": "You cannot update your own role"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Check while updating user roles
        requested_project_member = ProjectMember.objects.select_for_update().get(
            project_id=project_id,
            workspace__slug=slug,
            member=request.user,
            is_active=True,
        )

        if "role" in request.data:
            # Only Admins can modify roles
            if requested_project_member.role < ROLE.ADMIN.value and not is_workspace_admin:
                return Response(
                    {"error": "You do not have permission to update roles"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Cannot modify a member whose role is equal to or higher than your own
            if project_member.role >= requested_project_member.role and not is_workspace_admin:
                return Response(
                    {"error": "You cannot update the role of a member with a role equal to or higher than your own"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            try:
                new_role = int(request.data.get("role"))
            except (TypeError, ValueError):
                return Response(
                    {"error": "Invalid project role"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Cannot assign a role equal to or higher than your own
            if new_role >= requested_project_member.role and not is_workspace_admin:
                return Response(
                    {"error": "You cannot assign a role equal to or higher than your own"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            try:
                effective_role = project_role_for_workspace_role(
                    workspace_role=target_workspace_role,
                    requested_role=new_role,
                )
            except ValueError:
                return Response(
                    {"error": "Invalid project role"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if effective_role != new_role:
                return Response(
                    {"error": "The project role must respect the member's external workspace role"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Guard privileged `is_active` mutations (member (de)activation). These are NOT
        # covered by the role block above, so without this check a GUEST could PATCH
        # {"is_active": false} while omitting "role" to deactivate any member — including
        # admins — and take over the project. Mirror the role block and destroy(): only a
        # project admin (or workspace admin) may (de)activate a member, and never one whose
        # role is equal to or higher than the requester's own.
        if "is_active" in request.data:
            if requested_project_member.role < ROLE.ADMIN.value and not is_workspace_admin:
                return Response(
                    {"error": "You do not have permission to update member status"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if project_member.role >= requested_project_member.role and not is_workspace_admin:
                return Response(
                    {"error": "You cannot update the status of a member with a role equal to or higher than your own"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = ProjectMemberSerializer(project_member, data=request.data, partial=True)

        if serializer.is_valid():
            next_role = serializer.validated_data.get("role", project_member.role)
            next_is_active = serializer.validated_data.get("is_active", project_member.is_active)
            if project_member.role == ROLE.ADMIN.value and (next_role != ROLE.ADMIN.value or not next_is_active):
                active_admins = list(
                    ProjectMember.objects.select_for_update().filter(
                        project=project,
                        role=ROLE.ADMIN.value,
                        is_active=True,
                    )
                )
                if len(active_admins) <= 1:
                    return Response(
                        {"error": "The project must retain at least one active administrator"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    @allow_permission([ROLE.ADMIN])
    def destroy(self, request, slug, project_id, pk):
        project = (
            Project.objects.using("default")
            .only("workspace_id")
            .get(
                pk=project_id,
                workspace__slug=slug,
            )
        )
        lock_active_identity_source(workspace_id=project.workspace_id)
        requester_workspace_member = lock_active_workspace_member(
            workspace_id=project.workspace_id,
            user_id=request.user.id,
        )
        if requester_workspace_member is None:
            return Response(
                {"error": "An active external workspace membership is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        project_member = ProjectMember.objects.select_for_update().get(
            project=project,
            pk=pk,
            is_active=True,
        )
        # check requesting user role
        requesting_project_member = ProjectMember.objects.select_for_update().get(
            workspace__slug=slug,
            member=request.user,
            project_id=project_id,
            is_active=True,
        )
        is_workspace_admin = requester_workspace_member.role == ROLE.ADMIN.value
        if requesting_project_member.role < ROLE.ADMIN.value and not is_workspace_admin:
            return Response(
                {"error": "You don't have the required permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # User cannot remove himself
        if str(project_member.id) == str(requesting_project_member.id):
            return Response(
                {"error": "You cannot remove yourself from the workspace. Please use leave workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # User cannot deactivate higher role
        if requesting_project_member.role < project_member.role:
            return Response(
                {"error": "You cannot remove a user having role higher than you"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if project_member.role == ROLE.ADMIN.value:
            active_admins = list(
                ProjectMember.objects.select_for_update().filter(
                    project=project,
                    role=ROLE.ADMIN.value,
                    is_active=True,
                )
            )
            if len(active_admins) <= 1:
                return Response(
                    {"error": "The project must retain at least one active administrator"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        project_member.is_active = False
        project_member.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def leave(self, request, slug, project_id):
        project = (
            Project.objects.using("default")
            .only("workspace_id")
            .get(
                pk=project_id,
                workspace__slug=slug,
            )
        )
        lock_active_identity_source(workspace_id=project.workspace_id)
        if (
            lock_active_workspace_member(
                workspace_id=project.workspace_id,
                user_id=request.user.id,
            )
            is None
        ):
            return Response(
                {"error": "An active external workspace membership is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        project_member = ProjectMember.objects.select_for_update().get(
            project=project,
            member=request.user,
            is_active=True,
        )

        if project_member.role == ROLE.ADMIN.value:
            active_admins = list(
                ProjectMember.objects.select_for_update().filter(
                    project=project,
                    role=ROLE.ADMIN.value,
                    is_active=True,
                )
            )
            if len(active_admins) <= 1:
                return Response(
                    {"error": "The project must retain at least one active administrator"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        project_member.is_active = False
        project_member.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectMemberUserEndpoint(BaseAPIView):
    def get(self, request, slug, project_id):
        project_member = ProjectMember.objects.get(
            project_id=project_id,
            workspace__slug=slug,
            member=request.user,
            member_id__in=active_workspace_members().filter(workspace__slug=slug).values("member_id"),
            is_active=True,
        )
        serializer = ProjectMemberSerializer(project_member)

        return Response(serializer.data, status=status.HTTP_200_OK)


class UserProjectRolesEndpoint(BaseAPIView):
    permission_classes = [WorkspaceUserPermission]
    use_read_replica = True

    def get(self, request, slug):
        project_members = ProjectMember.objects.filter(
            workspace__slug=slug,
            member_id=request.user.id,
            is_active=True,
            member_id__in=active_workspace_members().filter(workspace__slug=slug).values("member_id"),
        ).values("project_id", "role")

        project_members = {str(member["project_id"]): member["role"] for member in project_members}
        return Response(project_members, status=status.HTTP_200_OK)


class ProjectMemberPreferenceEndpoint(BaseAPIView):
    def get_queryset(self, slug, project_id, member_id):
        return ProjectMember.objects.get(
            project_id=project_id,
            member_id=member_id,
            workspace__slug=slug,
            is_active=True,
            member_id__in=active_workspace_members().filter(workspace__slug=slug).values("member_id"),
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def patch(self, request, slug, project_id, member_id):
        project_member = self.get_queryset(slug, project_id, member_id)

        serializer = ProjectMemberPreferenceSerializer(project_member, {"preferences": request.data}, partial=True)

        if serializer.is_valid():
            preferences = serializer.validated_data["preferences"]
            ProjectMember.objects.filter(pk=project_member.pk).update(
                preferences=preferences,
                updated_at=timezone.now(),
            )
            return Response({"preferences": preferences}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, member_id):
        project_member = self.get_queryset(slug, project_id, member_id)

        serializer = ProjectMemberPreferenceSerializer(project_member)

        return Response(serializer.data, status=status.HTTP_200_OK)

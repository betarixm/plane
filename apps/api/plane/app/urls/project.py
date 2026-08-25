# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.app.views import (
    ProjectViewSet,
    DeployBoardViewSet,
    ProjectMemberViewSet,
    ProjectMemberUserEndpoint,
    ProjectUserViewsEndpoint,
    ProjectIdentifierEndpoint,
    ProjectFavoritesViewSet,
    UserProjectJoinViewSet,
    UserProjectRolesEndpoint,
    ProjectArchiveUnarchiveEndpoint,
    ProjectMemberPreferenceEndpoint,
)


urlpatterns = [
    path(
        "workspace/projects/",
        ProjectViewSet.as_view({"get": "list", "post": "create"}),
        name="project",
    ),
    path(
        "workspace/projects/details/",
        ProjectViewSet.as_view({"get": "list_detail"}),
        name="project",
    ),
    path(
        "workspace/projects/<uuid:pk>/",
        ProjectViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project",
    ),
    path(
        "workspace/project-identifiers/",
        ProjectIdentifierEndpoint.as_view(),
        name="project-identifiers",
    ),
    path(
        "users/me/workspace/projects/join/",
        UserProjectJoinViewSet.as_view({"post": "create"}),
        name="user-project-join",
    ),
    path(
        "users/me/workspace/project-roles/",
        UserProjectRolesEndpoint.as_view(),
        name="user-project-roles",
    ),
    path(
        "workspace/projects/<uuid:project_id>/members/",
        ProjectMemberViewSet.as_view({"get": "list", "post": "create"}),
        name="project-member",
    ),
    path(
        "workspace/projects/<uuid:project_id>/members/<uuid:pk>/",
        ProjectMemberViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="project-member",
    ),
    path(
        "workspace/projects/<uuid:project_id>/members/leave/",
        ProjectMemberViewSet.as_view({"post": "leave"}),
        name="project-member",
    ),
    path(
        "workspace/projects/<uuid:project_id>/project-views/",
        ProjectUserViewsEndpoint.as_view(),
        name="project-view",
    ),
    path(
        "workspace/projects/<uuid:project_id>/project-members/me/",
        ProjectMemberUserEndpoint.as_view(),
        name="project-member-view",
    ),
    path(
        "workspace/user-favorite-projects/",
        ProjectFavoritesViewSet.as_view({"get": "list", "post": "create"}),
        name="project-favorite",
    ),
    path(
        "workspace/user-favorite-projects/<uuid:project_id>/",
        ProjectFavoritesViewSet.as_view({"delete": "destroy"}),
        name="project-favorite",
    ),
    path(
        "workspace/projects/<uuid:project_id>/project-deploy-boards/",
        DeployBoardViewSet.as_view({"get": "list", "post": "create"}),
        name="project-deploy-board",
    ),
    path(
        "workspace/projects/<uuid:project_id>/project-deploy-boards/<uuid:pk>/",
        DeployBoardViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="project-deploy-board",
    ),
    path(
        "workspace/projects/<uuid:project_id>/archive/",
        ProjectArchiveUnarchiveEndpoint.as_view(),
        name="project-archive-unarchive",
    ),
    path(
        "workspace/projects/<uuid:project_id>/preferences/member/<uuid:member_id>/",
        ProjectMemberPreferenceEndpoint.as_view(),
        name="project-member-preference",
    ),
]

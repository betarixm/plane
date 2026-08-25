# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.api.views import (
    ProjectMemberListCreateAPIEndpoint,
    ProjectMemberDetailAPIEndpoint,
    ProjectMemberLiteAPIEndpoint,
    WorkspaceMemberAPIEndpoint,
    WorkspaceMemberLiteAPIEndpoint,
)

urlpatterns = [
    # Project members
    path(
        "workspace/projects/<uuid:project_id>/members/",
        ProjectMemberListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="project-members",
    ),
    path(
        "workspace/projects/<uuid:project_id>/members/<uuid:pk>/",
        ProjectMemberDetailAPIEndpoint.as_view(http_method_names=["patch", "delete", "get"]),
        name="project-member",
    ),
    path(
        "workspace/projects/<uuid:project_id>/project-members/",
        ProjectMemberListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="project-members",
    ),
    path(
        "workspace/projects/<uuid:project_id>/project-members-lite/",
        ProjectMemberLiteAPIEndpoint.as_view(http_method_names=["get"]),
        name="project-members-lite",
    ),
    path(
        "workspace/projects/<uuid:project_id>/project-members/<uuid:pk>/",
        ProjectMemberDetailAPIEndpoint.as_view(http_method_names=["patch", "delete", "get"]),
        name="project-member",
    ),
    path(
        "workspace/members/",
        WorkspaceMemberAPIEndpoint.as_view(http_method_names=["get"]),
        name="workspace-members",
    ),
    path(
        "workspace/members-lite/",
        WorkspaceMemberLiteAPIEndpoint.as_view(http_method_names=["get"]),
        name="workspace-members-lite",
    ),
]

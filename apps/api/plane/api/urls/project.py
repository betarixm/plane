# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.api.views import (
    ProjectListCreateAPIEndpoint,
    ProjectListLiteAPIEndpoint,
    ProjectDetailAPIEndpoint,
    ProjectArchiveUnarchiveAPIEndpoint,
    ProjectSummaryAPIEndpoint,
)

urlpatterns = [
    path(
        "workspace/projects/",
        ProjectListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="project",
    ),
    path(
        "workspace/projects-lite/",
        ProjectListLiteAPIEndpoint.as_view(http_method_names=["get"]),
        name="project-lite",
    ),
    path(
        "workspace/projects/<uuid:pk>/",
        ProjectDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="project",
    ),
    path(
        "workspace/projects/<uuid:project_id>/archive/",
        ProjectArchiveUnarchiveAPIEndpoint.as_view(http_method_names=["post", "delete"]),
        name="project-archive-unarchive",
    ),
    path(
        "workspace/projects/<uuid:project_id>/summary/",
        ProjectSummaryAPIEndpoint.as_view(http_method_names=["get"]),
        name="project-summary",
    ),
]

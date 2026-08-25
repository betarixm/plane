# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.api.views import (
    IntakeIssueListCreateAPIEndpoint,
    IntakeIssueDetailAPIEndpoint,
)


urlpatterns = [
    path(
        "workspace/projects/<uuid:project_id>/intake-issues/",
        IntakeIssueListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="intake-issue",
    ),
    path(
        "workspace/projects/<uuid:project_id>/intake-issues/<uuid:issue_id>/",
        IntakeIssueDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="intake-issue",
    ),
]

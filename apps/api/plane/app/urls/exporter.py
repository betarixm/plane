# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.app.views import ExportIssuesEndpoint


urlpatterns = [
    path(
        "workspace/export-issues/",
        ExportIssuesEndpoint.as_view(),
        name="export-issues",
    ),
]

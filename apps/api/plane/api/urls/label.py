# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.api.views import LabelListCreateAPIEndpoint, LabelDetailAPIEndpoint


urlpatterns = [
    path(
        "workspace/projects/<uuid:project_id>/labels/",
        LabelListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="label",
    ),
    path(
        "workspace/projects/<uuid:project_id>/labels/<uuid:pk>/",
        LabelDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="label",
    ),
]

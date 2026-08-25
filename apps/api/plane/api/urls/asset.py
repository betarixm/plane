# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.api.views import GenericAssetEndpoint

urlpatterns = [
    path(
        "workspace/assets/",
        GenericAssetEndpoint.as_view(http_method_names=["post"]),
        name="generic-asset",
    ),
    path(
        "workspace/assets/<uuid:asset_id>/",
        GenericAssetEndpoint.as_view(http_method_names=["get", "patch"]),
        name="generic-asset-detail",
    ),
]

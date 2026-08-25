# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import (
    FileAssetEndpoint,
    FileAssetViewSet,
    # V2 Endpoints
    WorkspaceFileAssetEndpoint,
    StaticFileAssetEndpoint,
    AssetRestoreEndpoint,
    ProjectAssetEndpoint,
    ProjectBulkAssetEndpoint,
    AssetCheckEndpoint,
    DuplicateAssetEndpoint,
    WorkspaceAssetDownloadEndpoint,
    ProjectAssetDownloadEndpoint,
)
from plane.middleware.singleton_workspace import singleton_workspace_path


urlpatterns = [
    singleton_workspace_path(
        "workspace/file-assets/",
        FileAssetEndpoint.as_view(),
        name="file-assets",
    ),
    singleton_workspace_path(
        "workspace/file-assets/<str:asset_key>/",
        FileAssetEndpoint.as_view(),
        name="file-assets",
        workspace_kwarg="workspace_id",
    ),
    singleton_workspace_path(
        "workspace/file-assets/<str:asset_key>/restore/",
        FileAssetViewSet.as_view({"post": "restore"}),
        name="file-assets-restore",
        workspace_kwarg="workspace_id",
    ),
    # V2 Endpoints
    singleton_workspace_path(
        "assets/v2/workspace/",
        WorkspaceFileAssetEndpoint.as_view(),
        name="workspace-file-assets",
    ),
    singleton_workspace_path(
        "assets/v2/workspace/<uuid:asset_id>/",
        WorkspaceFileAssetEndpoint.as_view(),
        name="workspace-file-assets",
    ),
    singleton_workspace_path(
        "assets/v2/workspace/restore/<uuid:asset_id>/",
        AssetRestoreEndpoint.as_view(),
        name="asset-restore",
    ),
    path(
        "assets/v2/static/<uuid:asset_id>/",
        StaticFileAssetEndpoint.as_view(),
        name="static-file-asset",
    ),
    singleton_workspace_path(
        "assets/v2/workspace/projects/<uuid:project_id>/",
        ProjectAssetEndpoint.as_view(),
        name="bulk-asset-update",
    ),
    singleton_workspace_path(
        "assets/v2/workspace/projects/<uuid:project_id>/<uuid:pk>/",
        ProjectAssetEndpoint.as_view(),
        name="bulk-asset-update",
    ),
    singleton_workspace_path(
        "assets/v2/workspace/projects/<uuid:project_id>/<uuid:entity_id>/bulk/",
        ProjectBulkAssetEndpoint.as_view(),
        name="bulk-asset-update",
    ),
    singleton_workspace_path(
        "assets/v2/workspace/check/<uuid:asset_id>/",
        AssetCheckEndpoint.as_view(),
        name="asset-check",
    ),
    singleton_workspace_path(
        "assets/v2/workspace/duplicate-assets/<uuid:asset_id>/",
        DuplicateAssetEndpoint.as_view(),
        name="duplicate-assets",
    ),
    singleton_workspace_path(
        "assets/v2/workspace/download/<uuid:asset_id>/",
        WorkspaceAssetDownloadEndpoint.as_view(),
        name="workspace-asset-download",
    ),
    singleton_workspace_path(
        "assets/v2/workspace/projects/<uuid:project_id>/download/<uuid:asset_id>/",
        ProjectAssetDownloadEndpoint.as_view(),
        name="project-asset-download",
    ),
]

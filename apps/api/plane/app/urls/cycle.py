# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path


from plane.app.views import (
    CycleViewSet,
    CycleIssueViewSet,
    CycleDateCheckEndpoint,
    CycleFavoriteViewSet,
    CycleProgressEndpoint,
    CycleAnalyticsEndpoint,
    TransferCycleIssueEndpoint,
    CycleUserPropertiesEndpoint,
    CycleArchiveUnarchiveEndpoint,
)


urlpatterns = [
    path(
        "workspace/projects/<uuid:project_id>/cycles/",
        CycleViewSet.as_view({"get": "list", "post": "create"}),
        name="project-cycle",
    ),
    path(
        "workspace/projects/<uuid:project_id>/cycles/<uuid:pk>/",
        CycleViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project-cycle",
    ),
    path(
        "workspace/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/cycle-issues/",
        CycleIssueViewSet.as_view({"get": "list", "post": "create"}),
        name="project-issue-cycle",
    ),
    path(
        "workspace/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/cycle-issues/<uuid:issue_id>/",
        CycleIssueViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project-issue-cycle",
    ),
    path(
        "workspace/projects/<uuid:project_id>/cycles/date-check/",
        CycleDateCheckEndpoint.as_view(),
        name="project-cycle-date",
    ),
    path(
        "workspace/projects/<uuid:project_id>/user-favorite-cycles/",
        CycleFavoriteViewSet.as_view({"get": "list", "post": "create"}),
        name="user-favorite-cycle",
    ),
    path(
        "workspace/projects/<uuid:project_id>/user-favorite-cycles/<uuid:cycle_id>/",
        CycleFavoriteViewSet.as_view({"delete": "destroy"}),
        name="user-favorite-cycle",
    ),
    path(
        "workspace/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/transfer-issues/",
        TransferCycleIssueEndpoint.as_view(),
        name="transfer-issues",
    ),
    path(
        "workspace/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/user-properties/",
        CycleUserPropertiesEndpoint.as_view(),
        name="cycle-user-filters",
    ),
    path(
        "workspace/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/archive/",
        CycleArchiveUnarchiveEndpoint.as_view(),
        name="cycle-archive-unarchive",
    ),
    path(
        "workspace/projects/<uuid:project_id>/archived-cycles/",
        CycleArchiveUnarchiveEndpoint.as_view(),
        name="cycle-archive-unarchive",
    ),
    path(
        "workspace/projects/<uuid:project_id>/archived-cycles/<uuid:pk>/",
        CycleArchiveUnarchiveEndpoint.as_view(),
        name="cycle-archive-unarchive",
    ),
    path(
        "workspace/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/progress/",
        CycleProgressEndpoint.as_view(),
        name="project-cycle",
    ),
    path(
        "workspace/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/analytics/",
        CycleAnalyticsEndpoint.as_view(),
        name="project-cycle",
    ),
]

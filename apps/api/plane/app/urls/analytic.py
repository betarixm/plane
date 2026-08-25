# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path


from plane.app.views import (
    AnalyticsEndpoint,
    AnalyticViewViewset,
    SavedAnalyticEndpoint,
    AdvanceAnalyticsEndpoint,
    AdvanceAnalyticsStatsEndpoint,
    AdvanceAnalyticsChartEndpoint,
    DefaultAnalyticsEndpoint,
    ProjectStatsEndpoint,
    ProjectAdvanceAnalyticsEndpoint,
    ProjectAdvanceAnalyticsStatsEndpoint,
    ProjectAdvanceAnalyticsChartEndpoint,
)


urlpatterns = [
    path(
        "workspace/analytics/",
        AnalyticsEndpoint.as_view(),
        name="plane-analytics",
    ),
    path(
        "workspace/analytic-view/",
        AnalyticViewViewset.as_view({"get": "list", "post": "create"}),
        name="analytic-view",
    ),
    path(
        "workspace/analytic-view/<uuid:pk>/",
        AnalyticViewViewset.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="analytic-view",
    ),
    path(
        "workspace/saved-analytic-view/<uuid:analytic_id>/",
        SavedAnalyticEndpoint.as_view(),
        name="saved-analytic-view",
    ),
    path(
        "workspace/default-analytics/",
        DefaultAnalyticsEndpoint.as_view(),
        name="default-analytics",
    ),
    path(
        "workspace/project-stats/",
        ProjectStatsEndpoint.as_view(),
        name="project-analytics",
    ),
    path(
        "workspace/advance-analytics/",
        AdvanceAnalyticsEndpoint.as_view(),
        name="advance-analytics",
    ),
    path(
        "workspace/advance-analytics-stats/",
        AdvanceAnalyticsStatsEndpoint.as_view(),
        name="advance-analytics-stats",
    ),
    path(
        "workspace/advance-analytics-charts/",
        AdvanceAnalyticsChartEndpoint.as_view(),
        name="advance-analytics-chart",
    ),
    path(
        "workspace/projects/<uuid:project_id>/advance-analytics/",
        ProjectAdvanceAnalyticsEndpoint.as_view(),
        name="project-advance-analytics",
    ),
    path(
        "workspace/projects/<uuid:project_id>/advance-analytics-stats/",
        ProjectAdvanceAnalyticsStatsEndpoint.as_view(),
        name="project-advance-analytics-stats",
    ),
    path(
        "workspace/projects/<uuid:project_id>/advance-analytics-charts/",
        ProjectAdvanceAnalyticsChartEndpoint.as_view(),
        name="project-advance-analytics-chart",
    ),
]

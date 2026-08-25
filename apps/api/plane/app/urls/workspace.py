# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.app.views import (
    ExportWorkspaceUserActivityEndpoint,
    QuickLinkViewSet,
    UserRecentVisitViewSet,
    WorkspaceCyclesEndpoint,
    WorkspaceDraftIssueViewSet,
    WorkspaceEstimatesEndpoint,
    WorkspaceFavoriteEndpoint,
    WorkspaceFavoriteGroupEndpoint,
    WorkspaceHomePreferenceViewSet,
    WorkspaceLabelsEndpoint,
    WorkspaceMemberUserEndpoint,
    WorkspaceMemberUserViewsEndpoint,
    WorkSpaceMemberViewSet,
    WorkspaceModulesEndpoint,
    WorkspaceProjectMemberEndpoint,
    WorkspaceStatesEndpoint,
    WorkspaceStickyViewSet,
    WorkspaceThemeViewSet,
    WorkspaceUserActivityEndpoint,
    WorkspaceUserPreferenceViewSet,
    WorkspaceUserProfileEndpoint,
    WorkspaceUserProfileIssuesEndpoint,
    WorkspaceUserProfileStatsEndpoint,
    WorkspaceUserPropertiesEndpoint,
    WorkSpaceViewSet,
)

urlpatterns = [
    path(
        "workspace/",
        WorkSpaceViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
            }
        ),
        name="workspace",
    ),
    # The configured external provider is the source of truth for the roster.
    path(
        "workspace/members/",
        WorkSpaceMemberViewSet.as_view({"get": "list"}),
        name="workspace-member",
    ),
    path(
        "workspace/project-members/",
        WorkspaceProjectMemberEndpoint.as_view(),
        name="workspace-member-roles",
    ),
    path(
        "workspace/members/<uuid:pk>/",
        WorkSpaceMemberViewSet.as_view({"get": "retrieve"}),
        name="workspace-member",
    ),
    path(
        "workspace/workspace-members/me/",
        WorkspaceMemberUserEndpoint.as_view(),
        name="workspace-member-details",
    ),
    path(
        "workspace/workspace-views/",
        WorkspaceMemberUserViewsEndpoint.as_view(),
        name="workspace-member-views-details",
    ),
    path(
        "workspace/workspace-themes/",
        WorkspaceThemeViewSet.as_view({"get": "list", "post": "create"}),
        name="workspace-themes",
    ),
    path(
        "workspace/workspace-themes/<uuid:pk>/",
        WorkspaceThemeViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="workspace-themes",
    ),
    path(
        "workspace/user-stats/<uuid:user_id>/",
        WorkspaceUserProfileStatsEndpoint.as_view(),
        name="workspace-user-stats",
    ),
    path(
        "workspace/user-activity/<uuid:user_id>/",
        WorkspaceUserActivityEndpoint.as_view(),
        name="workspace-user-activity",
    ),
    path(
        "workspace/user-activity/<uuid:user_id>/export/",
        ExportWorkspaceUserActivityEndpoint.as_view(),
        name="export-workspace-user-activity",
    ),
    path(
        "workspace/user-profile/<uuid:user_id>/",
        WorkspaceUserProfileEndpoint.as_view(),
        name="workspace-user-profile-page",
    ),
    path(
        "workspace/user-issues/<uuid:user_id>/",
        WorkspaceUserProfileIssuesEndpoint.as_view(),
        name="workspace-user-profile-issues",
    ),
    path(
        "workspace/labels/",
        WorkspaceLabelsEndpoint.as_view(),
        name="workspace-labels",
    ),
    path(
        "workspace/user-properties/",
        WorkspaceUserPropertiesEndpoint.as_view(),
        name="workspace-user-filters",
    ),
    path(
        "workspace/states/",
        WorkspaceStatesEndpoint.as_view(),
        name="workspace-state",
    ),
    path(
        "workspace/estimates/",
        WorkspaceEstimatesEndpoint.as_view(),
        name="workspace-estimate",
    ),
    path(
        "workspace/modules/",
        WorkspaceModulesEndpoint.as_view(),
        name="workspace-modules",
    ),
    path(
        "workspace/cycles/",
        WorkspaceCyclesEndpoint.as_view(),
        name="workspace-cycles",
    ),
    path(
        "workspace/user-favorites/",
        WorkspaceFavoriteEndpoint.as_view(),
        name="workspace-user-favorites",
    ),
    path(
        "workspace/user-favorites/<uuid:favorite_id>/",
        WorkspaceFavoriteEndpoint.as_view(),
        name="workspace-user-favorites",
    ),
    path(
        "workspace/user-favorites/<uuid:favorite_id>/group/",
        WorkspaceFavoriteGroupEndpoint.as_view(),
        name="workspace-user-favorites-groups",
    ),
    path(
        "workspace/draft-issues/",
        WorkspaceDraftIssueViewSet.as_view({"get": "list", "post": "create"}),
        name="workspace-draft-issues",
    ),
    path(
        "workspace/draft-issues/<uuid:pk>/",
        WorkspaceDraftIssueViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="workspace-drafts-issues",
    ),
    path(
        "workspace/draft-to-issue/<uuid:draft_id>/",
        WorkspaceDraftIssueViewSet.as_view({"post": "create_draft_to_issue"}),
        name="workspace-drafts-issues",
    ),
    # quick link
    path(
        "workspace/quick-links/",
        QuickLinkViewSet.as_view({"get": "list", "post": "create"}),
        name="workspace-quick-links",
    ),
    path(
        "workspace/quick-links/<uuid:pk>/",
        QuickLinkViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="workspace-quick-links",
    ),
    # Widgets
    path(
        "workspace/home-preferences/",
        WorkspaceHomePreferenceViewSet.as_view(),
        name="workspace-home-preference",
    ),
    path(
        "workspace/home-preferences/<str:key>/",
        WorkspaceHomePreferenceViewSet.as_view(),
        name="workspace-home-preference",
    ),
    path(
        "workspace/recent-visits/",
        UserRecentVisitViewSet.as_view({"get": "list"}),
        name="workspace-recent-visits",
    ),
    path(
        "workspace/stickies/",
        WorkspaceStickyViewSet.as_view({"get": "list", "post": "create"}),
        name="workspace-sticky",
    ),
    path(
        "workspace/stickies/<uuid:pk>/",
        WorkspaceStickyViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="workspace-sticky",
    ),
    # User Preference
    path(
        "workspace/sidebar-preferences/",
        WorkspaceUserPreferenceViewSet.as_view(),
        name="workspace-user-preference",
    ),
]

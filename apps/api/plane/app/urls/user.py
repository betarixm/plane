# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import (
    ProfileEndpoint,
    UserActivityEndpoint,
    UserActivityGraphEndpoint,
    ## User
    UserEndpoint,
    UserIssueCompletedGraphEndpoint,
    UserWorkspaceDashboardEndpoint,
    ## End User
    ## Workspaces
    UserWorkspaceEndpoint,
)
from plane.middleware.singleton_workspace import singleton_workspace_path

urlpatterns = [
    # User Profile
    path(
        "users/me/",
        UserEndpoint.as_view({"get": "retrieve"}),
        name="users",
    ),
    path(
        "users/me/settings/",
        UserEndpoint.as_view({"get": "retrieve_user_settings"}),
        name="users",
    ),
    # Profile
    path("users/me/profile/", ProfileEndpoint.as_view(), name="accounts"),
    # End profile
    path("users/me/activities/", UserActivityEndpoint.as_view(), name="user-activities"),
    # singleton workspace membership
    path("users/me/workspace/", UserWorkspaceEndpoint.as_view(), name="user-workspace"),
    # User Graphs
    singleton_workspace_path(
        "users/me/workspace/activity-graph/",
        UserActivityGraphEndpoint.as_view(),
        name="user-activity-graph",
    ),
    singleton_workspace_path(
        "users/me/workspace/issues-completed-graph/",
        UserIssueCompletedGraphEndpoint.as_view(),
        name="completed-graph",
    ),
    singleton_workspace_path(
        "users/me/workspace/dashboard/",
        UserWorkspaceDashboardEndpoint.as_view(),
        name="user-workspace-dashboard",
    ),
    ## End User Graph
]

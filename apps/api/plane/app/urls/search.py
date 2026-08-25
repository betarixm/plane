# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path


from plane.app.views import GlobalSearchEndpoint, IssueSearchEndpoint, SearchEndpoint


urlpatterns = [
    path(
        "workspace/search/",
        GlobalSearchEndpoint.as_view(),
        name="global-search",
    ),
    path(
        "workspace/projects/<uuid:project_id>/search-issues/",
        IssueSearchEndpoint.as_view(),
        name="project-issue-search",
    ),
    path(
        "workspace/entity-search/",
        SearchEndpoint.as_view(),
        name="entity-search",
    ),
]

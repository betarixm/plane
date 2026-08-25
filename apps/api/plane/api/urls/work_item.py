# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.api.views import (
    IssueListCreateAPIEndpoint,
    IssueDetailAPIEndpoint,
    IssueLinkListCreateAPIEndpoint,
    IssueLinkDetailAPIEndpoint,
    IssueCommentListCreateAPIEndpoint,
    IssueCommentDetailAPIEndpoint,
    IssueActivityListAPIEndpoint,
    IssueActivityDetailAPIEndpoint,
    IssueAttachmentListCreateAPIEndpoint,
    IssueAttachmentDetailAPIEndpoint,
    WorkspaceIssueAPIEndpoint,
    IssueSearchEndpoint,
    IssueRelationListCreateAPIEndpoint,
)

# Deprecated url patterns
old_url_patterns = [
    path(
        "workspace/issues/search/",
        IssueSearchEndpoint.as_view(http_method_names=["get"]),
        name="issue-search",
    ),
    path(
        "workspace/issues/<str:project_identifier>-<str:issue_identifier>/",
        WorkspaceIssueAPIEndpoint.as_view(http_method_names=["get"]),
        name="issue-by-identifier",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/",
        IssueListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="issue",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:pk>/",
        IssueDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="issue",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/links/",
        IssueLinkListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="link",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/links/<uuid:pk>/",
        IssueLinkDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="link",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/comments/",
        IssueCommentListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="comment",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/comments/<uuid:pk>/",
        IssueCommentDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="comment",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/activities/",
        IssueActivityListAPIEndpoint.as_view(http_method_names=["get"]),
        name="activity",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/activities/<uuid:pk>/",
        IssueActivityDetailAPIEndpoint.as_view(http_method_names=["get"]),
        name="activity",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/issue-attachments/",
        IssueAttachmentListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="attachment",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/issue-attachments/<uuid:pk>/",
        IssueAttachmentDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="issue-attachment",
    ),
]

# New url patterns with work-items as the prefix
new_url_patterns = [
    path(
        "workspace/work-items/search/",
        IssueSearchEndpoint.as_view(http_method_names=["get"]),
        name="work-item-search",
    ),
    path(
        "workspace/work-items/<str:project_identifier>-<str:issue_identifier>/",
        WorkspaceIssueAPIEndpoint.as_view(http_method_names=["get"]),
        name="work-item-by-identifier",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/",
        IssueListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="work-item-list",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:pk>/",
        IssueDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="work-item-detail",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:issue_id>/links/",
        IssueLinkListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="work-item-link-list",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:issue_id>/links/<uuid:pk>/",
        IssueLinkDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="work-item-link-detail",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:issue_id>/comments/",
        IssueCommentListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="work-item-comment-list",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:issue_id>/comments/<uuid:pk>/",
        IssueCommentDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="work-item-comment-detail",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:issue_id>/activities/",
        IssueActivityListAPIEndpoint.as_view(http_method_names=["get"]),
        name="work-item-activity-list",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:issue_id>/activities/<uuid:pk>/",
        IssueActivityDetailAPIEndpoint.as_view(http_method_names=["get"]),
        name="work-item-activity-detail",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:issue_id>/attachments/",
        IssueAttachmentListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="work-item-attachment-list",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:issue_id>/attachments/<uuid:pk>/",
        IssueAttachmentDetailAPIEndpoint.as_view(http_method_names=["get", "patch", "delete"]),
        name="work-item-attachment-detail",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:issue_id>/relations/",
        IssueRelationListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="work-item-relation-list",
    ),
]

urlpatterns = old_url_patterns + new_url_patterns

# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.app.views import (
    BulkCreateIssueLabelsEndpoint,
    BulkDeleteIssuesEndpoint,
    SubIssuesEndpoint,
    IssueLinkViewSet,
    IssueAttachmentEndpoint,
    CommentReactionViewSet,
    IssueActivityEndpoint,
    IssueArchiveViewSet,
    IssueCommentViewSet,
    IssueListEndpoint,
    IssueReactionViewSet,
    IssueRelationViewSet,
    IssueSubscriberViewSet,
    ProjectUserDisplayPropertyEndpoint,
    IssueViewSet,
    LabelViewSet,
    BulkArchiveIssuesEndpoint,
    DeletedIssuesListViewSet,
    IssuePaginatedViewSet,
    IssueDetailEndpoint,
    IssueAttachmentV2Endpoint,
    IssueBulkUpdateDateEndpoint,
    IssueVersionEndpoint,
    WorkItemDescriptionVersionEndpoint,
    IssueMetaEndpoint,
    IssueDetailIdentifierEndpoint,
)

urlpatterns = [
    path(
        "workspace/projects/<uuid:project_id>/issues/list/",
        IssueListEndpoint.as_view(),
        name="project-issue",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/",
        IssueViewSet.as_view({"get": "list", "post": "create"}),
        name="project-issue",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues-detail/",
        IssueDetailEndpoint.as_view(),
        name="project-issue-detail",
    ),
    # updated v1 paginated issues
    # updated v2 paginated issues
    path(
        "workspace/projects/<uuid:project_id>/v2/issues/",
        IssuePaginatedViewSet.as_view({"get": "list"}),
        name="project-issues-paginated",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:pk>/",
        IssueViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project-issue",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issue-labels/",
        LabelViewSet.as_view({"get": "list", "post": "create"}),
        name="project-issue-labels",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issue-labels/<uuid:pk>/",
        LabelViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project-issue-labels",
    ),
    path(
        "workspace/projects/<uuid:project_id>/bulk-create-labels/",
        BulkCreateIssueLabelsEndpoint.as_view(),
        name="project-bulk-labels",
    ),
    path(
        "workspace/projects/<uuid:project_id>/bulk-delete-issues/",
        BulkDeleteIssuesEndpoint.as_view(),
        name="project-issues-bulk",
    ),
    path(
        "workspace/projects/<uuid:project_id>/bulk-archive-issues/",
        BulkArchiveIssuesEndpoint.as_view(),
        name="bulk-archive-issues",
    ),
    ##
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/sub-issues/",
        SubIssuesEndpoint.as_view(),
        name="sub-issues",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/issue-links/",
        IssueLinkViewSet.as_view({"get": "list", "post": "create"}),
        name="project-issue-links",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/issue-links/<uuid:pk>/",
        IssueLinkViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project-issue-links",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/issue-attachments/",
        IssueAttachmentEndpoint.as_view(),
        name="project-issue-attachments",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/issue-attachments/<uuid:pk>/",
        IssueAttachmentEndpoint.as_view(),
        name="project-issue-attachments",
    ),
    # V2 Attachments
    path(
        "assets/v2/workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/attachments/",
        IssueAttachmentV2Endpoint.as_view(),
        name="project-issue-attachments",
    ),
    path(
        "assets/v2/workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/attachments/<uuid:pk>/",
        IssueAttachmentV2Endpoint.as_view(),
        name="project-issue-attachments",
    ),
    ## End Issues
    ## Issue Activity
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/history/",
        IssueActivityEndpoint.as_view(),
        name="project-issue-history",
    ),
    ## Issue Activity
    ## IssueComments
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/comments/",
        IssueCommentViewSet.as_view({"get": "list", "post": "create"}),
        name="project-issue-comment",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/comments/<uuid:pk>/",
        IssueCommentViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project-issue-comment",
    ),
    ## End IssueComments
    # Issue Subscribers
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/issue-subscribers/",
        IssueSubscriberViewSet.as_view({"get": "list", "post": "create"}),
        name="project-issue-subscribers",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/issue-subscribers/<uuid:subscriber_id>/",
        IssueSubscriberViewSet.as_view({"delete": "destroy"}),
        name="project-issue-subscribers",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/subscribe/",
        IssueSubscriberViewSet.as_view({"get": "subscription_status", "post": "subscribe", "delete": "unsubscribe"}),
        name="project-issue-subscribers",
    ),
    ## End Issue Subscribers
    # Issue Reactions
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/reactions/",
        IssueReactionViewSet.as_view({"get": "list", "post": "create"}),
        name="project-issue-reactions",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/reactions/<str:reaction_code>/",
        IssueReactionViewSet.as_view({"delete": "destroy"}),
        name="project-issue-reactions",
    ),
    ## End Issue Reactions
    # Comment Reactions
    path(
        "workspace/projects/<uuid:project_id>/comments/<uuid:comment_id>/reactions/",
        CommentReactionViewSet.as_view({"get": "list", "post": "create"}),
        name="project-issue-comment-reactions",
    ),
    path(
        "workspace/projects/<uuid:project_id>/comments/<uuid:comment_id>/reactions/<str:reaction_code>/",
        CommentReactionViewSet.as_view({"delete": "destroy"}),
        name="project-issue-comment-reactions",
    ),
    ## End Comment Reactions
    ## ProjectUserProperty
    path(
        "workspace/projects/<uuid:project_id>/user-properties/",
        ProjectUserDisplayPropertyEndpoint.as_view(),
        name="project-issue-display-properties",
    ),
    ## ProjectUserProperty End
    ## Issue Archives
    path(
        "workspace/projects/<uuid:project_id>/archived-issues/",
        IssueArchiveViewSet.as_view({"get": "list"}),
        name="project-issue-archive",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:pk>/archive/",
        IssueArchiveViewSet.as_view({"get": "retrieve", "post": "archive", "delete": "unarchive"}),
        name="project-issue-archive-unarchive",
    ),
    ## End Issue Archives
    ## Issue Relation
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/issue-relation/",
        IssueRelationViewSet.as_view({"get": "list", "post": "create"}),
        name="issue-relation",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/remove-relation/",
        IssueRelationViewSet.as_view({"post": "remove_relation"}),
        name="issue-relation",
    ),
    ## End Issue Relation
    path(
        "workspace/projects/<uuid:project_id>/deleted-issues/",
        DeletedIssuesListViewSet.as_view(),
        name="deleted-issues",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issue-dates/",
        IssueBulkUpdateDateEndpoint.as_view(),
        name="project-issue-dates",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/versions/",
        IssueVersionEndpoint.as_view(),
        name="issue-versions",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/versions/<uuid:pk>/",
        IssueVersionEndpoint.as_view(),
        name="issue-versions",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:work_item_id>/description-versions/",
        WorkItemDescriptionVersionEndpoint.as_view(),
        name="work-item-versions",
    ),
    path(
        "workspace/projects/<uuid:project_id>/work-items/<uuid:work_item_id>/description-versions/<uuid:pk>/",
        WorkItemDescriptionVersionEndpoint.as_view(),
        name="work-item-versions",
    ),
    path(
        "workspace/projects/<uuid:project_id>/issues/<uuid:issue_id>/meta/",
        IssueMetaEndpoint.as_view(),
        name="issue-meta",
    ),
    path(
        "workspace/work-items/<str:project_identifier>-<str:issue_identifier>/",
        IssueDetailIdentifierEndpoint.as_view(),
        name="issue-detail-identifier",
    ),
]

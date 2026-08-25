# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.middleware.singleton_workspace import singleton_workspace_path as path

from plane.app.views import (
    WebhookEndpoint,
    WebhookLogsEndpoint,
    WebhookSecretRegenerateEndpoint,
)


urlpatterns = [
    path("workspace/webhooks/", WebhookEndpoint.as_view(), name="webhooks"),
    path(
        "workspace/webhooks/<uuid:pk>/",
        WebhookEndpoint.as_view(),
        name="webhooks",
    ),
    path(
        "workspace/webhooks/<uuid:pk>/regenerate/",
        WebhookSecretRegenerateEndpoint.as_view(),
        name="webhooks",
    ),
    path(
        "workspace/webhook-logs/<uuid:webhook_id>/",
        WebhookLogsEndpoint.as_view(),
        name="webhooks",
    ),
]

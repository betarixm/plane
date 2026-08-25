# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from .views import (
    CSRFTokenEndpoint,
    SignOutAuthEndpoint,
    SignOutAuthSpaceEndpoint,
    SlackEventsEndpoint,
    SlackInstallCallbackEndpoint,
    SlackInstallEndpoint,
    SlackLoginCallbackEndpoint,
    SlackLoginEndpoint,
)

urlpatterns = [
    # Slack is the only interactive identity provider. Installation bootstraps
    # the singleton workspace; regular OIDC is used for every later login.
    path("slack/install/", SlackInstallEndpoint.as_view(), name="slack-install"),
    path(
        "slack/install/callback/",
        SlackInstallCallbackEndpoint.as_view(),
        name="slack-install-callback",
    ),
    path("slack/", SlackLoginEndpoint.as_view(), name="slack-login"),
    path(
        "slack/callback/",
        SlackLoginCallbackEndpoint.as_view(),
        name="slack-login-callback",
    ),
    path("slack/events/", SlackEventsEndpoint.as_view(), name="slack-events"),
    # Session lifecycle remains local even though identity is externally owned.
    path("sign-out/", SignOutAuthEndpoint.as_view(), name="sign-out"),
    path("spaces/sign-out/", SignOutAuthSpaceEndpoint.as_view(), name="space-sign-out"),
    path("get-csrf-token/", CSRFTokenEndpoint.as_view(), name="get_csrf_token"),
]

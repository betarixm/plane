# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.license.api.views import (
    DisableEmailFeatureEndpoint,
    EmailCredentialCheckEndpoint,
    InstanceConfigurationEndpoint,
    InstanceEndpoint,
    InstanceSetupEndpoint,
    InstanceWorkspaceEndpoint,
)

urlpatterns = [
    path("", InstanceEndpoint.as_view(), name="instance"),
    path("setup/", InstanceSetupEndpoint.as_view(), name="instance-setup"),
    path(
        "configurations/",
        InstanceConfigurationEndpoint.as_view(),
        name="instance-configuration",
    ),
    path(
        "configurations/disable-email-feature/",
        DisableEmailFeatureEndpoint.as_view(),
        name="disable-email-configuration",
    ),
    path(
        "email-credentials-check/",
        EmailCredentialCheckEndpoint.as_view(),
        name="email-credential-check",
    ),
    path("workspace/", InstanceWorkspaceEndpoint.as_view(), name="instance-workspace"),
]

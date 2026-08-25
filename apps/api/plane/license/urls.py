# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.license.api.views import InstanceEndpoint

urlpatterns = [
    path("", InstanceEndpoint.as_view(), name="instance"),
]

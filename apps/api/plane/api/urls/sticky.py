# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import include
from rest_framework.routers import DefaultRouter

from plane.api.views import StickyViewSet
from plane.middleware.singleton_workspace import singleton_workspace_path as path


router = DefaultRouter()
router.register(r"stickies", StickyViewSet, basename="workspace-stickies")

urlpatterns = [
    path("workspace/", include(router.urls)),
]

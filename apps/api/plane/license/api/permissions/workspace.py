# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework.permissions import BasePermission

from plane.utils.workspace_admin import is_workspace_admin


class WorkspaceAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return is_workspace_admin(request.user)

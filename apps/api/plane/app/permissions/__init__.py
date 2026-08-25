# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from .base import ROLE, allow_permission
from .project import (
    ProjectAdminPermission,
    ProjectBasePermission,
    ProjectEntityPermission,
    ProjectLitePermission,
    ProjectMemberPermission,
)
from .workspace import (
    WorkSpaceAdminPermission,
    WorkspaceAdminPermission,
    WorkSpaceBasePermission,
    WorkspaceEntityPermission,
    WorkspaceMemberPermission,
    WorkspaceUserPermission,
    WorkspaceViewerPermission,
)

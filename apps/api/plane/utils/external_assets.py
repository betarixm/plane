# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.db.models import FileAsset


EXTERNALLY_MANAGED_ASSET_ENTITY_TYPES = frozenset(
    {
        FileAsset.EntityTypeContext.USER_AVATAR,
        FileAsset.EntityTypeContext.USER_COVER,
        FileAsset.EntityTypeContext.WORKSPACE_LOGO,
    }
)
EXTERNALLY_MANAGED_ASSET_ERROR = (
    "The external identity provider manages user avatars, user covers, and "
    "workspace logos."
)


def is_externally_managed_asset_entity_type(entity_type) -> bool:
    """Return whether the external identity provider owns this asset type."""

    return (
        isinstance(entity_type, str)
        and entity_type in EXTERNALLY_MANAGED_ASSET_ENTITY_TYPES
    )

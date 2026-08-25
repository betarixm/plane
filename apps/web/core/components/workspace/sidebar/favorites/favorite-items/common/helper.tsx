/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { FAVORITE_ITEM_LINKS } from "@plane/constants";
import type { IFavorite } from "@plane/types";

export const generateFavoriteItemLink = (favorite: IFavorite) => {
  const entityLinkDetails = FAVORITE_ITEM_LINKS[favorite.entity_type];

  if (!entityLinkDetails) {
    console.error(`Unrecognized favorite entity type: ${favorite.entity_type}`);
    return `/home`;
  }

  if (entityLinkDetails.itemLevel === "workspace") {
    return `/${entityLinkDetails.getLink(favorite)}`;
  } else if (entityLinkDetails.itemLevel === "project") {
    return `/projects/${favorite.project_id}/${entityLinkDetails.getLink(favorite)}`;
  } else {
    return `/home`;
  }
};

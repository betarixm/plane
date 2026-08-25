/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { IFavorite } from "@plane/types";
// helpers
// services
import { APIService } from "@/services/api.service";
// types

export class FavoriteService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async addFavorite(data: Partial<IFavorite>): Promise<IFavorite> {
    return this.post(`/api/workspace/user-favorites/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updateFavorite(favoriteId: string, data: Partial<IFavorite>): Promise<IFavorite> {
    return this.patch(`/api/workspace/user-favorites/${favoriteId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async deleteFavorite(favoriteId: string): Promise<void> {
    return this.delete(`/api/workspace/user-favorites/${favoriteId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async getFavorites(): Promise<IFavorite[]> {
    return this.get(`/api/workspace/user-favorites/`, {
      params: {
        all: true,
      },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getGroupedFavorites(favoriteId: string): Promise<IFavorite[]> {
    return this.get(`/api/workspace/user-favorites/${favoriteId}/group/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

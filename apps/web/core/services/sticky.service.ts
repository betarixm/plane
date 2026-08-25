/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// helpers
import { STICKIES_PER_PAGE, API_BASE_URL } from "@plane/constants";
import type { TSticky } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export class StickyService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async createSticky(payload: Partial<TSticky>) {
    return this.post(`/api/workspace/stickies/`, payload)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async getStickies(
    cursor: string,
    query?: string,
    per_page?: number
  ): Promise<{ results: TSticky[]; total_pages: number }> {
    return this.get(`/api/workspace/stickies/`, {
      params: {
        cursor,
        per_page: per_page || STICKIES_PER_PAGE,
        query,
      },
    })
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async getSticky(id: string) {
    return this.get(`/api/workspace/stickies/${id}`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async updateSticky(id: string, data: Partial<TSticky>) {
    return await this.patch(`/api/workspace/stickies/${id}/`, data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async deleteSticky(id: string) {
    return await this.delete(`/api/workspace/stickies/${id}`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }
}

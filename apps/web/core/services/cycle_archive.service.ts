/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// type
import { API_BASE_URL } from "@plane/constants";
import type { ICycle } from "@plane/types";
// helpers
// services
import { APIService } from "@/services/api.service";

export class CycleArchiveService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getArchivedCycles(projectId: string): Promise<ICycle[]> {
    return this.get(`/api/workspace/projects/${projectId}/archived-cycles/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getArchivedCycleDetails(projectId: string, cycleId: string): Promise<ICycle> {
    return this.get(`/api/workspace/projects/${projectId}/archived-cycles/${cycleId}/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async archiveCycle(
    projectId: string,
    cycleId: string
  ): Promise<{
    archived_at: string;
  }> {
    return this.post(`/api/workspace/projects/${projectId}/cycles/${cycleId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async restoreCycle(projectId: string, cycleId: string): Promise<void> {
    return this.delete(`/api/workspace/projects/${projectId}/cycles/${cycleId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

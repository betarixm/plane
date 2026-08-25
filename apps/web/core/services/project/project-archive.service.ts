/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// helpers
import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export class ProjectArchiveService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async archiveProject(projectId: string): Promise<{
    archived_at: string;
  }> {
    return this.post(`/api/workspace/projects/${projectId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async restoreProject(projectId: string): Promise<void> {
    return this.delete(`/api/workspace/projects/${projectId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

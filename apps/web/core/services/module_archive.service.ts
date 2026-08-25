/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// type
import { API_BASE_URL } from "@plane/constants";
import type { IModule } from "@plane/types";
// helpers
// services
import { APIService } from "@/services/api.service";

export class ModuleArchiveService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getArchivedModules(projectId: string): Promise<IModule[]> {
    return this.get(`/api/workspace/projects/${projectId}/archived-modules/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getArchivedModuleDetails(projectId: string, moduleId: string): Promise<IModule> {
    return this.get(`/api/workspace/projects/${projectId}/archived-modules/${moduleId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async archiveModule(
    projectId: string,
    moduleId: string
  ): Promise<{
    archived_at: string;
  }> {
    return this.post(`/api/workspace/projects/${projectId}/modules/${moduleId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async restoreModule(projectId: string, moduleId: string): Promise<void> {
    return this.delete(`/api/workspace/projects/${projectId}/modules/${moduleId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

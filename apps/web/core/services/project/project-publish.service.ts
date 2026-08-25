/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// types
import { API_BASE_URL } from "@plane/constants";
import type { TProjectPublishSettings } from "@plane/types";
// helpers
// services
import { APIService } from "@/services/api.service";

export class ProjectPublishService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchPublishSettings(projectID: string): Promise<TProjectPublishSettings> {
    return this.get(`/api/workspace/projects/${projectID}/project-deploy-boards/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async publishProject(projectID: string, data: Partial<TProjectPublishSettings>): Promise<TProjectPublishSettings> {
    return this.post(`/api/workspace/projects/${projectID}/project-deploy-boards/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updatePublishSettings(
    projectID: string,
    project_publish_id: string,
    data: Partial<TProjectPublishSettings>
  ): Promise<TProjectPublishSettings> {
    return this.patch(`/api/workspace/projects/${projectID}/project-deploy-boards/${project_publish_id}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async unpublishProject(projectID: string, project_publish_id: string): Promise<any> {
    return this.delete(`/api/workspace/projects/${projectID}/project-deploy-boards/${project_publish_id}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }
}

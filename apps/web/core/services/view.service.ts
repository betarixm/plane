/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { IProjectView } from "@plane/types";
import { APIService } from "@/services/api.service";
// types
// helpers

export class ViewService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async createView(projectId: string, data: Partial<IProjectView>): Promise<any> {
    return this.post(`/api/workspace/projects/${projectId}/views/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async patchView(projectId: string, viewId: string, data: Partial<IProjectView>): Promise<any> {
    return this.patch(`/api/workspace/projects/${projectId}/views/${viewId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteView(projectId: string, viewId: string): Promise<any> {
    return this.delete(`/api/workspace/projects/${projectId}/views/${viewId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getViews(projectId: string): Promise<IProjectView[]> {
    return this.get(`/api/workspace/projects/${projectId}/views/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getViewDetails(projectId: string, viewId: string): Promise<IProjectView> {
    return this.get(`/api/workspace/projects/${projectId}/views/${viewId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getViewIssues(projectId: string, viewId: string): Promise<any> {
    return this.get(`/api/workspace/projects/${projectId}/views/${viewId}/issues/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async addViewToFavorites(
    projectId: string,
    data: {
      view: string;
    }
  ): Promise<any> {
    return this.post(`/api/workspace/projects/${projectId}/user-favorite-views/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async removeViewFromFavorites(projectId: string, viewId: string): Promise<any> {
    return this.delete(`/api/workspace/projects/${projectId}/user-favorite-views/${viewId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

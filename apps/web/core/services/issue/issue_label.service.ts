/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { IIssueLabel } from "@plane/types";
// services
import { APIService } from "@/services/api.service";
// types

export class IssueLabelService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getWorkspaceIssueLabels(): Promise<IIssueLabel[]> {
    return this.get(`/api/workspace/labels/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getProjectLabels(projectId: string): Promise<IIssueLabel[]> {
    return this.get(`/api/workspace/projects/${projectId}/issue-labels/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createIssueLabel(projectId: string, data: any): Promise<IIssueLabel> {
    return this.post(`/api/workspace/projects/${projectId}/issue-labels/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async patchIssueLabel(projectId: string, labelId: string, data: any): Promise<any> {
    return this.patch(`/api/workspace/projects/${projectId}/issue-labels/${labelId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteIssueLabel(projectId: string, labelId: string): Promise<any> {
    return this.delete(`/api/workspace/projects/${projectId}/issue-labels/${labelId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// services
import { API_BASE_URL } from "@plane/constants";
import type { IIssueFiltersResponse } from "@plane/types";
import { APIService } from "@/services/api.service";
// types

export class IssueFiltersService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  // epic issue filters
  async fetchProjectEpicFilters(projectId: string): Promise<IIssueFiltersResponse> {
    return this.get(`/api/workspace/projects/${projectId}/epics-user-properties/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
  async patchProjectEpicFilters(projectId: string, data: Partial<IIssueFiltersResponse>): Promise<any> {
    return this.patch(`/api/workspace/projects/${projectId}/epics-user-properties/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  // cycle issue filters
  async fetchCycleIssueFilters(projectId: string, cycleId: string): Promise<IIssueFiltersResponse> {
    return this.get(`/api/workspace/projects/${projectId}/cycles/${cycleId}/user-properties/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
  async patchCycleIssueFilters(projectId: string, cycleId: string, data: Partial<IIssueFiltersResponse>): Promise<any> {
    return this.patch(`/api/workspace/projects/${projectId}/cycles/${cycleId}/user-properties/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  // module issue filters
  async fetchModuleIssueFilters(projectId: string, moduleId: string): Promise<IIssueFiltersResponse> {
    return this.get(`/api/workspace/projects/${projectId}/modules/${moduleId}/user-properties/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
  async patchModuleIssueFilters(
    projectId: string,
    moduleId: string,
    data: Partial<IIssueFiltersResponse>
  ): Promise<any> {
    return this.patch(`/api/workspace/projects/${projectId}/modules/${moduleId}/user-properties/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

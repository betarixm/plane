/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// services
import { API_BASE_URL } from "@plane/constants";
import type { IIntakeState, IState } from "@plane/types";
import { APIService } from "@/services/api.service";
// helpers
// types

export class ProjectStateService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async createState(projectId: string, data: any): Promise<IState> {
    return this.post(`/api/workspace/projects/${projectId}/states/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async markDefault(projectId: string, stateId: string): Promise<void> {
    return this.post(`/api/workspace/projects/${projectId}/states/${stateId}/mark-default/`, {})
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async getStates(projectId: string): Promise<IState[]> {
    return this.get(`/api/workspace/projects/${projectId}/states/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getIntakeState(projectId: string): Promise<IIntakeState> {
    return this.get(`/api/workspace/projects/${projectId}/intake-state/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getState(projectId: string, stateId: string): Promise<any> {
    return this.get(`/api/workspace/projects/${projectId}/states/${stateId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateState(projectId: string, stateId: string, data: IState): Promise<any> {
    return this.put(`/api/workspace/projects/${projectId}/states/${stateId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async patchState(projectId: string, stateId: string, data: Partial<IState>): Promise<any> {
    return this.patch(`/api/workspace/projects/${projectId}/states/${stateId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteState(projectId: string, stateId: string): Promise<any> {
    return this.delete(`/api/workspace/projects/${projectId}/states/${stateId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async getWorkspaceStates(): Promise<IState[]> {
    return this.get(`/api/workspace/states/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

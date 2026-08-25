/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* eslint-disable no-useless-catch */

// types
import { API_BASE_URL } from "@plane/constants";
import type { IEstimate, IEstimateFormData, IEstimatePoint } from "@plane/types";
// helpers
// services
import { APIService } from "@/services/api.service";

export class EstimateService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchWorkspaceEstimates(): Promise<IEstimate[] | undefined> {
    try {
      const { data } = await this.get(`/api/workspace/estimates/`);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async fetchProjectEstimates(projectId: string): Promise<IEstimate[] | undefined> {
    try {
      const { data } = await this.get(`/api/workspace/projects/${projectId}/estimates/`);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async fetchEstimateById(projectId: string, estimateId: string): Promise<IEstimate | undefined> {
    try {
      const { data } = await this.get(`/api/workspace/projects/${projectId}/estimates/${estimateId}/`);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async createEstimate(projectId: string, payload: IEstimateFormData): Promise<IEstimate | undefined> {
    try {
      const { data } = await this.post(`/api/workspace/projects/${projectId}/estimates/`, payload);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async deleteEstimate(projectId: string, estimateId: string): Promise<void> {
    try {
      await this.delete(`/api/workspace/projects/${projectId}/estimates/${estimateId}/`);
    } catch (error) {
      throw error;
    }
  }

  async createEstimatePoint(
    projectId: string,
    estimateId: string,
    payload: Partial<IEstimatePoint>
  ): Promise<IEstimatePoint | undefined> {
    try {
      const { data } = await this.post(
        `/api/workspace/projects/${projectId}/estimates/${estimateId}/estimate-points/`,
        payload
      );
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async updateEstimatePoint(
    projectId: string,
    estimateId: string,
    estimatePointId: string,
    payload: Partial<IEstimatePoint>
  ): Promise<IEstimatePoint | undefined> {
    try {
      const { data } = await this.patch(
        `/api/workspace/projects/${projectId}/estimates/${estimateId}/estimate-points/${estimatePointId}/`,
        payload
      );
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }
}
const estimateService = new EstimateService();

export default estimateService;

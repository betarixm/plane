/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { ICycle } from "@plane/types";
import { APIService } from "../api.service";

/**
 * Service class for managing archived cycles in a project
 * Provides methods for retrieving, archiving, and restoring project cycles
 * @extends {APIService}
 */
export class CycleArchiveService extends APIService {
  constructor(BASE_URL?: string) {
    super(BASE_URL || API_BASE_URL);
  }

  /**
   * Retrieves all archived cycles for a specific project
   * @param {string} projectId - The unique identifier for the project
   * @returns {Promise<ICycle[]>} Array of archived cycles
   * @throws {Error} Throws response data if the request fails
   */
  async list(projectId: string): Promise<ICycle[]> {
    return this.get(`/api/workspace/projects/${projectId}/archived-cycles/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Retrieves details of a specific archived cycle
   * @param {string} projectId - The unique identifier for the project
   * @param {string} cycleId - The unique identifier for the cycle
   * @returns {Promise<ICycle>} Details of the archived cycle
   * @throws {Error} Throws response data if the request fails
   */
  async retrieve(projectId: string, cycleId: string): Promise<ICycle> {
    return this.get(`/api/workspace/projects/${projectId}/archived-cycles/${cycleId}/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /**
   * Archives a specific cycle in a project
   * @param {string} projectId - The unique identifier for the project
   * @param {string} cycleId - The unique identifier for the cycle to archive
   * @returns {Promise<{archived_at: string}>} Object containing the archive timestamp
   * @throws {Error} Throws response data if the request fails
   */
  async archive(
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

  /**
   * Restores a previously archived cycle
   * @param {string} projectId - The unique identifier for the project
   * @param {string} cycleId - The unique identifier for the cycle to restore
   * @returns {Promise<void>} Resolves when the cycle is successfully restored
   * @throws {Error} Throws response data if the request fails
   */
  async restore(projectId: string, cycleId: string): Promise<void> {
    return this.delete(`/api/workspace/projects/${projectId}/cycles/${cycleId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { IWorkspace, IWorkspaceSearchResults } from "@plane/types";
import { APIService } from "../api.service";

/**
 * Service class for managing workspace operations
 * Handles singleton workspace reads, updates, and related functionality
 * @extends {APIService}
 */
export class WorkspaceService extends APIService {
  /**
   * Creates an instance of WorkspaceService
   * @param {string} baseUrl - The base URL for API requests
   */
  constructor(BASE_URL?: string) {
    super(BASE_URL || API_BASE_URL);
  }
  /**
   * Retrieves details of a specific workspace
   * @param {string} workspaceSlug - The unique slug identifier for the workspace
   * @returns {Promise<IWorkspace>} Promise resolving to workspace details
   * @throws {Error} If the API request fails
   */
  async retrieve(workspaceSlug: string): Promise<IWorkspace> {
    return this.get(`/api/workspaces/${workspaceSlug}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  /**
   * Updates an existing workspace
   * @param {string} workspaceSlug - The unique slug identifier for the workspace
   * @param {Partial<IWorkspace>} data - Updated workspace data
   * @returns {Promise<IWorkspace>} Promise resolving to the updated workspace
   * @throws {Error} If the API request fails
   */
  async update(workspaceSlug: string, data: Partial<IWorkspace>): Promise<IWorkspace> {
    return this.patch(`/api/workspaces/${workspaceSlug}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Searches within a workspace
   * @param {string} workspaceSlug - The unique slug identifier for the workspace
   * @param {Object} params - Search parameters
   * @param {string} [params.project_id] - Optional project ID to scope the search
   * @param {string} params.search - Search query string
   * @param {boolean} params.workspace_search - Whether to search across the entire workspace
   * @returns {Promise<IWorkspaceSearchResults>} Promise resolving to search results
   * @throws {Error} If the API request fails
   */
  async search(
    workspaceSlug: string,
    params: {
      project_id?: string;
      search: string;
      workspace_search: boolean;
    }
  ): Promise<IWorkspaceSearchResults> {
    return this.get(`/api/workspaces/${workspaceSlug}/search/`, {
      params,
    })
      .then((res) => res?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

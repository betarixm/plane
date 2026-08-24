/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { IWorkspace } from "@plane/types";
import { APIService } from "../api.service";

/**
 * Service class for reading the instance workspace
 * Reads the workspace attached to this instance
 * @extends APIService
 */
export class InstanceWorkspaceService extends APIService {
  /**
   * Constructor for InstanceWorkspaceService
   * @param BASE_URL - Base URL for API requests
   */
  constructor(BASE_URL?: string) {
    super(BASE_URL || API_BASE_URL);
  }

  async retrieve(): Promise<IWorkspace> {
    return this.get("/api/instances/workspace/")
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

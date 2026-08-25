/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
import type { IUser } from "@plane/types";
// api service
import { APIService } from "../api.service";

/**
 * Service class for managing user operations
 * Handles operations for retrieving the current user's details and perform CRUD operations
 * @extends {APIService}
 */
export class UserService extends APIService {
  /**
   * Constructor for UserService
   * @param BASE_URL - Base URL for API requests
   */
  constructor(BASE_URL?: string) {
    super(BASE_URL || API_BASE_URL);
  }

  /**
   * Retrieves the current user details
   * @returns {Promise<IUser>} Promise resolving to the current user details
   */
  async me(): Promise<IUser> {
    return this.get("/api/users/me/")
      .then((response) => response?.data)
      .catch((error) => {
        throw error;
      });
  }
}

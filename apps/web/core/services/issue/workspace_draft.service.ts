/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TIssue, TWorkspaceDraftIssue, TWorkspaceDraftPaginationInfo } from "@plane/types";
// helpers
// services
import { APIService } from "@/services/api.service";

export class WorkspaceDraftService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getIssues(query: object = {}): Promise<TWorkspaceDraftPaginationInfo<TWorkspaceDraftIssue> | undefined> {
    return this.get(`/api/workspace/draft-issues/`, { params: { ...query } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getIssueById(issueId: string): Promise<TWorkspaceDraftIssue | undefined> {
    return this.get(`/api/workspace/draft-issues/${issueId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async createIssue(payload: Partial<TWorkspaceDraftIssue | TIssue>): Promise<TWorkspaceDraftIssue | undefined> {
    return this.post(`/api/workspace/draft-issues/`, payload)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updateIssue(
    issueId: string,
    payload: Partial<TWorkspaceDraftIssue | TIssue>
  ): Promise<TWorkspaceDraftIssue | undefined> {
    return this.patch(`/api/workspace/draft-issues/${issueId}/`, payload)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async deleteIssue(issueId: string): Promise<void> {
    return this.delete(`/api/workspace/draft-issues/${issueId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async moveIssue(issueId: string, payload: Partial<TWorkspaceDraftIssue>): Promise<TIssue> {
    return this.post(`/api/workspace/draft-to-issue/${issueId}/`, payload)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }
}

const workspaceDraftService = new WorkspaceDraftService();

export default workspaceDraftService;

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { API_BASE_URL } from "@plane/constants";
import type { TInboxIssue, TIssue, TInboxIssueWithPagination } from "@plane/types";
import { EInboxIssueSource } from "@plane/types";
// helpers
// services
import { APIService } from "@/services/api.service";

export class InboxIssueService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async list(projectId: string, params = {}): Promise<TInboxIssueWithPagination> {
    return this.get(`/api/workspace/projects/${projectId}/inbox-issues/`, {
      params,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async retrieve(projectId: string, inboxIssueId: string): Promise<TInboxIssue> {
    return this.get(`/api/workspace/projects/${projectId}/inbox-issues/${inboxIssueId}/?expand=issue_inbox`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(projectId: string, data: Partial<TIssue>): Promise<TInboxIssue> {
    return this.post(`/api/workspace/projects/${projectId}/inbox-issues/`, {
      source: EInboxIssueSource.IN_APP,
      issue: data,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(projectId: string, inboxIssueId: string, data: Partial<TInboxIssue>): Promise<TInboxIssue> {
    return this.patch(`/api/workspace/projects/${projectId}/inbox-issues/${inboxIssueId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateIssue(projectId: string, inboxIssueId: string, data: Partial<TIssue>): Promise<TInboxIssue> {
    return this.patch(`/api/workspace/projects/${projectId}/inbox-issues/${inboxIssueId}/`, {
      issue: data,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async destroy(projectId: string, inboxIssueId: string): Promise<void> {
    return this.delete(`/api/workspace/projects/${projectId}/inbox-issues/${inboxIssueId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

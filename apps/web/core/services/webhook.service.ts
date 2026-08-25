/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// api services
import { API_BASE_URL } from "@plane/constants";
import type { IWebhook } from "@plane/types";
import { APIService } from "@/services/api.service";
// helpers
// types

export class WebhookService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchWebhooksList(): Promise<IWebhook[]> {
    return this.get(`/api/workspace/webhooks/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchWebhookDetails(webhookId: string): Promise<IWebhook> {
    return this.get(`/api/workspace/webhooks/${webhookId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createWebhook(data = {}): Promise<IWebhook> {
    return this.post(`/api/workspace/webhooks/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateWebhook(webhookId: string, data = {}): Promise<IWebhook> {
    return this.patch(`/api/workspace/webhooks/${webhookId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteWebhook(webhookId: string): Promise<void> {
    return this.delete(`/api/workspace/webhooks/${webhookId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async regenerateSecretKey(webhookId: string): Promise<IWebhook> {
    return this.post(`/api/workspace/webhooks/${webhookId}/regenerate/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

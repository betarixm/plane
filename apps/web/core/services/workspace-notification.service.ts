/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* eslint-disable no-useless-catch */

import { API_BASE_URL } from "@plane/constants";
import type {
  TNotificationPaginatedInfo,
  TNotificationPaginatedInfoQueryParams,
  TNotification,
  TUnreadNotificationsCount,
} from "@plane/types";
// helpers
// services
import { APIService } from "@/services/api.service";

export class WorkspaceNotificationService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchUnreadNotificationsCount(): Promise<TUnreadNotificationsCount | undefined> {
    try {
      const { data } = await this.get(`/api/workspace/users/notifications/unread/`);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async fetchNotifications(
    params: TNotificationPaginatedInfoQueryParams
  ): Promise<TNotificationPaginatedInfo | undefined> {
    try {
      const { data } = await this.get(`/api/workspace/users/notifications/`, {
        params,
      });
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async updateNotificationById(
    notificationId: string,
    payload: Partial<TNotification>
  ): Promise<TNotification | undefined> {
    try {
      const { data } = await this.patch(`/api/workspace/users/notifications/${notificationId}/`, payload);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async markNotificationAsRead(notificationId: string): Promise<TNotification | undefined> {
    try {
      const { data } = await this.post(`/api/workspace/users/notifications/${notificationId}/read/`);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async markNotificationAsUnread(notificationId: string): Promise<TNotification | undefined> {
    try {
      const { data } = await this.delete(`/api/workspace/users/notifications/${notificationId}/read/`);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async markNotificationAsArchived(notificationId: string): Promise<TNotification | undefined> {
    try {
      const { data } = await this.post(`/api/workspace/users/notifications/${notificationId}/archive/`);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async markNotificationAsUnArchived(notificationId: string): Promise<TNotification | undefined> {
    try {
      const { data } = await this.delete(`/api/workspace/users/notifications/${notificationId}/archive/`);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }

  async markAllNotificationsAsRead(payload: TNotificationPaginatedInfoQueryParams): Promise<TNotification | undefined> {
    try {
      const { data } = await this.post(`/api/workspace/users/notifications/mark-all-read/`, payload);
      return data || undefined;
    } catch (error) {
      throw error;
    }
  }
}

const workspaceNotificationService = new WorkspaceNotificationService();

export default workspaceNotificationService;

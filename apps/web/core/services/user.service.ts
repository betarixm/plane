/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// services
import { API_BASE_URL } from "@plane/constants";
import type {
  TIssue,
  IUser,
  IUserActivityResponse,
  IUserProfileData,
  IUserProfileProjectSegregation,
  IUserSettings,
  IUserEmailNotificationSettings,
  TIssuesResponse,
  TUserProfile,
} from "@plane/types";
import { APIService } from "@/services/api.service";
// types
// helpers

export class UserService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  currentUserConfig() {
    return {
      url: `${this.baseURL}/api/users/me/`,
    };
  }

  async userIssues(
    workspaceSlug: string,
    params: any
  ): Promise<
    | {
        [key: string]: TIssue[];
      }
    | TIssue[]
  > {
    return this.get(`/api/workspaces/${workspaceSlug}/my-issues/`, {
      params,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async currentUser(): Promise<IUser> {
    // Using validateStatus: null to bypass interceptors for unauthorized errors.
    return this.get("/api/users/me/", { validateStatus: null })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async getCurrentUserProfile(): Promise<TUserProfile> {
    return this.get("/api/users/me/profile/")
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }
  async updateCurrentUserProfile(data: any): Promise<any> {
    return this.patch("/api/users/me/profile/", data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async currentUserSettings(bustCache: boolean = false): Promise<IUserSettings> {
    const url = bustCache ? `/api/users/me/settings/?t=${Date.now()}` : "/api/users/me/settings/";
    return this.get(url)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async currentUserEmailNotificationSettings(): Promise<IUserEmailNotificationSettings> {
    return this.get("/api/users/me/notification-preferences/")
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updateCurrentUserEmailNotificationSettings(data: Partial<IUserEmailNotificationSettings>): Promise<any> {
    return this.patch("/api/users/me/notification-preferences/", data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getUserProfileData(workspaceSlug: string, userId: string): Promise<IUserProfileData> {
    return this.get(`/api/workspaces/${workspaceSlug}/user-stats/${userId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getUserProfileProjectsSegregation(
    workspaceSlug: string,
    userId: string
  ): Promise<IUserProfileProjectSegregation> {
    return this.get(`/api/workspaces/${workspaceSlug}/user-profile/${userId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getUserProfileActivity(
    workspaceSlug: string,
    userId: string,
    params: {
      per_page: number;
      cursor?: string;
    }
  ): Promise<IUserActivityResponse> {
    return this.get(`/api/workspaces/${workspaceSlug}/user-activity/${userId}/`, {
      params,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async downloadProfileActivity(
    workspaceSlug: string,
    userId: string,
    data: {
      date: string;
    }
  ): Promise<any> {
    return this.post(`/api/workspaces/${workspaceSlug}/user-activity/${userId}/export/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getUserProfileIssues(
    workspaceSlug: string,
    userId: string,
    params: any,
    config = {}
  ): Promise<TIssuesResponse> {
    return this.get(
      `/api/workspaces/${workspaceSlug}/user-issues/${userId}/`,
      {
        params,
      },
      config
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async joinProject(workspaceSlug: string, project_ids: string[]): Promise<any> {
    return this.post(`/api/users/me/workspaces/${workspaceSlug}/projects/join/`, { project_ids })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async leaveProject(workspaceSlug: string, projectId: string) {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/members/leave/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

const userService = new UserService();

export default userService;

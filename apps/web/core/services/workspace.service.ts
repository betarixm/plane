/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  IWorkspace,
  IWorkspaceMemberMe,
  IWorkspaceMember,
  IWorkspaceSearchResults,
  IProductUpdateResponse,
  IWorkspaceViewProps,
  IUserProjectsRole,
  IWorkspaceView,
  TIssuesResponse,
  TLink,
  TSearchResponse,
  TSearchEntityRequestPayload,
  TWidgetEntityData,
  TActivityEntityData,
  IWorkspaceSidebarNavigationItem,
  IWorkspaceSidebarNavigation,
  IWorkspaceUserPropertiesResponse,
} from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export class WorkspaceService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async userWorkspace(): Promise<IWorkspace | undefined> {
    return this.get("/api/users/me/workspace/")
      .then((response) => response?.data)
      .catch((error) => {
        if (error?.response?.status === 404) return undefined;
        throw error?.response?.data;
      });
  }

  async updateWorkspace(data: Pick<IWorkspace, "timezone">): Promise<IWorkspace> {
    return this.patch(`/api/workspace/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async workspaceMemberMe(): Promise<IWorkspaceMemberMe> {
    return this.get(`/api/workspace/workspace-members/me/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updateWorkspaceView(data: { view_props: IWorkspaceViewProps }): Promise<any> {
    return this.post(`/api/workspace/workspace-views/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchWorkspaceMembers(): Promise<IWorkspaceMember[]> {
    return this.get(`/api/workspace/members/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async searchWorkspace(params: {
    project_id?: string;
    search: string;
    workspace_search: boolean;
  }): Promise<IWorkspaceSearchResults> {
    return this.get(`/api/workspace/search/`, {
      params,
    })
      .then((res) => res?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
  async getProductUpdates(): Promise<IProductUpdateResponse[]> {
    return this.get("/api/release-notes/")
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createView(data: Partial<IWorkspaceView>): Promise<IWorkspaceView> {
    return this.post(`/api/workspace/views/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateView(viewId: string, data: Partial<IWorkspaceView>): Promise<IWorkspaceView> {
    return this.patch(`/api/workspace/views/${viewId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteView(viewId: string): Promise<any> {
    return this.delete(`/api/workspace/views/${viewId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getAllViews(): Promise<IWorkspaceView[]> {
    return this.get(`/api/workspace/views/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getViewDetails(viewId: string): Promise<IWorkspaceView> {
    return this.get(`/api/workspace/views/${viewId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getViewIssues(params: any, config = {}): Promise<TIssuesResponse> {
    const path = params.expand?.includes("issue_relation") ? `/api/workspace/issues-detail/` : `/api/workspace/issues/`;
    return this.get(
      path,
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

  async getWorkspaceUserProjectsRole(): Promise<IUserProjectsRole> {
    return this.get(`/api/users/me/workspace/project-roles/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  // quicklinks
  async fetchWorkspaceLinks(): Promise<TLink[]> {
    return this.get(`/api/workspace/quick-links/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async createWorkspaceLink(data: Partial<TLink>): Promise<TLink> {
    return this.post(`/api/workspace/quick-links/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updateWorkspaceLink(linkId: string, data: Partial<TLink>): Promise<TLink> {
    return this.patch(`/api/workspace/quick-links/${linkId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async deleteWorkspaceLink(linkId: string): Promise<void> {
    return this.delete(`/api/workspace/quick-links/${linkId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async searchEntity(params: TSearchEntityRequestPayload): Promise<TSearchResponse> {
    return this.get(`/api/workspace/entity-search/`, {
      params: {
        ...params,
        query_type: params.query_type.join(","),
      },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  // recents
  async fetchWorkspaceRecents(entity_name?: string): Promise<TActivityEntityData[]> {
    return this.get(`/api/workspace/recent-visits/`, {
      params: {
        entity_name,
      },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  // widgets
  async fetchWorkspaceWidgets(): Promise<TWidgetEntityData[]> {
    return this.get(`/api/workspace/home-preferences/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updateWorkspaceWidget(widgetKey: string, data: Partial<TWidgetEntityData>): Promise<TWidgetEntityData> {
    return this.patch(`/api/workspace/home-preferences/${widgetKey}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async fetchSidebarNavigationPreferences(): Promise<IWorkspaceSidebarNavigation> {
    return this.get(`/api/workspace/sidebar-preferences/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updateSidebarPreference(
    key: string,
    data: Partial<IWorkspaceSidebarNavigationItem>
  ): Promise<IWorkspaceSidebarNavigationItem> {
    return this.patch(`/api/workspace/sidebar-preferences/${key}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updateBulkSidebarPreferences(
    data: Array<{ key: string; is_pinned: boolean; sort_order: number }>
  ): Promise<IWorkspaceSidebarNavigation> {
    return this.patch(`/api/workspace/sidebar-preferences/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async fetchWorkspaceFilters(): Promise<IWorkspaceUserPropertiesResponse> {
    return this.get(`/api/workspace/user-properties/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async patchWorkspaceFilters(
    data: Partial<IWorkspaceUserPropertiesResponse>
  ): Promise<IWorkspaceUserPropertiesResponse> {
    return this.patch(`/api/workspace/user-properties/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { clone, set } from "lodash-es";
import { action, computed, observable, makeObservable, runInAction } from "mobx";
// types
import { computedFn } from "mobx-utils";
import type {
  IWorkspaceSidebarNavigationItem,
  IWorkspace,
  IWorkspaceSidebarNavigation,
  IWorkspaceUserPropertiesResponse,
} from "@plane/types";
// services
import { WorkspaceService } from "@/services/workspace.service";
// store
import type { CoreRootStore } from "@/store/root.store";
// sub-stores
import type { IApiTokenStore } from "./api-token.store";
import { ApiTokenStore } from "./api-token.store";
import type { IHomeStore } from "./home";
import { HomeStore } from "./home";
import type { IWebhookStore } from "./webhook.store";
import { WebhookStore } from "./webhook.store";

export interface IWorkspaceRootStore {
  loader: boolean;
  workspace: IWorkspace | undefined;
  // computed
  currentWorkspace: IWorkspace | null;
  navigationPreferencesMap: Record<string, IWorkspaceSidebarNavigation>;
  projectNavigationPreferencesMap: Record<string, IWorkspaceUserPropertiesResponse>;
  getWorkspaceRedirectionUrl: () => string;
  // computed actions
  getWorkspaceBySlug: (workspaceSlug: string) => IWorkspace | null;
  getWorkspaceById: (workspaceId: string) => IWorkspace | null;
  // fetch actions
  fetchWorkspace: () => Promise<IWorkspace | undefined>;
  // update actions
  updateWorkspace: (workspaceSlug: string, data: Partial<IWorkspace>) => Promise<IWorkspace>;
  updateWorkspaceLogo: (workspaceSlug: string, logoURL: string) => void;
  fetchSidebarNavigationPreferences: (workspaceSlug: string) => Promise<void>;
  updateSidebarPreference: (
    workspaceSlug: string,
    key: string,
    data: Partial<IWorkspaceSidebarNavigationItem>
  ) => Promise<IWorkspaceSidebarNavigationItem | undefined>;
  updateBulkSidebarPreferences: (
    workspaceSlug: string,
    data: Array<{ key: string; is_pinned: boolean; sort_order: number }>
  ) => Promise<void>;
  getNavigationPreferences: (workspaceSlug: string) => IWorkspaceSidebarNavigation | undefined;
  getProjectNavigationPreferences: (workspaceSlug: string) => IWorkspaceUserPropertiesResponse | undefined;
  fetchProjectNavigationPreferences: (workspaceSlug: string) => Promise<void>;
  updateProjectNavigationPreferences: (
    workspaceSlug: string,
    data: Partial<IWorkspaceUserPropertiesResponse>
  ) => Promise<void>;
  mutateWorkspaceMembersActivity: (workspaceSlug: string) => Promise<void>;
  // sub-stores
  webhook: IWebhookStore;
  apiToken: IApiTokenStore;
  home: IHomeStore;
}

export class BaseWorkspaceRootStore implements IWorkspaceRootStore {
  loader: boolean = false;
  workspace: IWorkspace | undefined = undefined;
  navigationPreferencesMap: Record<string, IWorkspaceSidebarNavigation> = {};
  projectNavigationPreferencesMap: Record<string, IWorkspaceUserPropertiesResponse> = {};
  // services
  workspaceService;
  // root store
  router;
  home;
  // sub-stores
  webhook: IWebhookStore;
  apiToken: IApiTokenStore;

  constructor(_rootStore: CoreRootStore) {
    makeObservable(this, {
      loader: observable.ref,
      // observables
      workspace: observable,
      navigationPreferencesMap: observable,
      projectNavigationPreferencesMap: observable,
      // computed
      currentWorkspace: computed,
      // computed actions
      getWorkspaceBySlug: action,
      getWorkspaceById: action,
      // actions
      fetchWorkspace: action,
      updateWorkspace: action,
      updateWorkspaceLogo: action,
      fetchSidebarNavigationPreferences: action,
      updateSidebarPreference: action,
      updateBulkSidebarPreferences: action,
      fetchProjectNavigationPreferences: action,
      updateProjectNavigationPreferences: action,
    });

    // services
    this.workspaceService = new WorkspaceService();
    // root store
    this.router = _rootStore.router;
    this.home = new HomeStore();
    // sub-stores
    this.webhook = new WebhookStore(_rootStore);
    this.apiToken = new ApiTokenStore(_rootStore);
  }

  /** Get the deterministic route for the instance workspace. */
  getWorkspaceRedirectionUrl = () => {
    return this.workspace ? `/${this.workspace.slug}` : "/invitations";
  };

  /**
   * computed value of current workspace based on workspace slug saved in the query store
   */
  get currentWorkspace() {
    const workspaceSlug = this.router.workspaceSlug;
    if (!workspaceSlug) return null;
    return this.workspace?.slug === workspaceSlug ? this.workspace : null;
  }

  /**
   * get the singleton workspace when its slug matches
   * @param workspaceSlug
   */
  getWorkspaceBySlug = (workspaceSlug: string) => (this.workspace?.slug === workspaceSlug ? this.workspace : null);

  /**
   * get the singleton workspace when its id matches
   * @param workspaceId
   */
  getWorkspaceById = (workspaceId: string) => (this.workspace?.id === workspaceId ? this.workspace : null);

  /**
   * fetch the user's singleton workspace from the API
   */
  fetchWorkspace = async () => {
    this.loader = true;
    try {
      const workspace = await this.workspaceService.userWorkspace();
      runInAction(() => {
        this.workspace = workspace;
      });
      return workspace;
    } finally {
      this.loader = false;
    }
  };

  /**
   * update workspace using the workspace slug and new workspace data
   * @param workspaceSlug
   * @param data
   */
  updateWorkspace = async (workspaceSlug: string, data: Partial<IWorkspace>) =>
    await this.workspaceService.updateWorkspace(workspaceSlug, data).then((res) => {
      if (res && res.id) {
        runInAction(() => {
          this.workspace = res;
        });
      }
      return res;
    });

  /**
   * update workspace using the workspace slug and new workspace data
   * @param {string} workspaceSlug
   * @param {string} logoURL
   */
  updateWorkspaceLogo = (workspaceSlug: string, logoURL: string) => {
    const workspace = this.workspace;
    if (workspace?.slug !== workspaceSlug) {
      throw new Error("Workspace not found");
    }
    runInAction(() => {
      set(workspace, ["logo_url"], logoURL);
    });
  };

  fetchSidebarNavigationPreferences = async (workspaceSlug: string) => {
    try {
      const response = await this.workspaceService.fetchSidebarNavigationPreferences(workspaceSlug);

      runInAction(() => {
        this.navigationPreferencesMap[workspaceSlug] = response;
      });
    } catch (error) {
      console.error("Failed to fetch sidebar preferences:", error);
    }
  };

  updateSidebarPreference = async (
    workspaceSlug: string,
    key: string,
    data: Partial<IWorkspaceSidebarNavigationItem>
  ) => {
    // Store the data before update to use for reverting if needed
    const beforeUpdateData = clone(this.navigationPreferencesMap[workspaceSlug]?.[key]);

    try {
      runInAction(() => {
        this.navigationPreferencesMap[workspaceSlug] = {
          ...this.navigationPreferencesMap[workspaceSlug],
          [key]: {
            ...beforeUpdateData,
            ...data,
          },
        };
      });

      const response = await this.workspaceService.updateSidebarPreference(workspaceSlug, key, data);
      return response;
    } catch (error) {
      // Revert to original data if API call fails
      runInAction(() => {
        this.navigationPreferencesMap[workspaceSlug] = {
          ...this.navigationPreferencesMap[workspaceSlug],
          [key]: beforeUpdateData,
        };
      });
      console.error("Failed to update sidebar preference:", error);
    }
  };

  getNavigationPreferences = computedFn(
    (workspaceSlug: string): IWorkspaceSidebarNavigation | undefined => this.navigationPreferencesMap[workspaceSlug]
  );

  updateBulkSidebarPreferences = async (
    workspaceSlug: string,
    data: Array<{ key: string; is_pinned: boolean; sort_order: number }>
  ) => {
    const beforeUpdateData = clone(this.navigationPreferencesMap[workspaceSlug]);

    try {
      // Optimistically update store
      const updatedPreferences: IWorkspaceSidebarNavigation = {};
      data.forEach((item) => {
        updatedPreferences[item.key] = item;
      });

      runInAction(() => {
        this.navigationPreferencesMap[workspaceSlug] = {
          ...this.navigationPreferencesMap[workspaceSlug],
          ...updatedPreferences,
        };
      });

      // Call API to persist changes
      await this.workspaceService.updateBulkSidebarPreferences(workspaceSlug, data);
    } catch (error) {
      // Rollback on failure
      runInAction(() => {
        this.navigationPreferencesMap[workspaceSlug] = beforeUpdateData;
      });
      console.error("Failed to update bulk sidebar preferences:", error);
      throw error;
    }
  };

  getProjectNavigationPreferences = computedFn(
    (workspaceSlug: string): IWorkspaceUserPropertiesResponse | undefined =>
      this.projectNavigationPreferencesMap[workspaceSlug]
  );

  fetchProjectNavigationPreferences = async (workspaceSlug: string) => {
    try {
      const response = await this.workspaceService.fetchWorkspaceFilters(workspaceSlug);

      runInAction(() => {
        this.projectNavigationPreferencesMap[workspaceSlug] = response;
      });
    } catch (error) {
      console.error("Failed to fetch project navigation preferences:", error);
      throw error;
    }
  };

  updateProjectNavigationPreferences = async (
    workspaceSlug: string,
    data: Partial<IWorkspaceUserPropertiesResponse>
  ) => {
    const beforeUpdateData = clone(this.projectNavigationPreferencesMap[workspaceSlug]);

    try {
      // Optimistically update store
      runInAction(() => {
        this.projectNavigationPreferencesMap[workspaceSlug] = {
          ...this.projectNavigationPreferencesMap[workspaceSlug],
          ...data,
        };
      });

      // Call API to persist changes
      await this.workspaceService.patchWorkspaceFilters(workspaceSlug, data);
    } catch (error) {
      // Rollback on failure
      runInAction(() => {
        this.projectNavigationPreferencesMap[workspaceSlug] = beforeUpdateData;
      });
      console.error("Failed to update project navigation preferences:", error);
      throw error;
    }
  };

  /**
   * Mutate workspace members activity — no-op in CE
   * @param workspaceSlug
   */
  mutateWorkspaceMembersActivity = async (_workspaceSlug: string): Promise<void> => {
    // No-op in default/CE version
  };
}

// Alias so consumers can keep using WorkspaceRootStore
export { BaseWorkspaceRootStore as WorkspaceRootStore };

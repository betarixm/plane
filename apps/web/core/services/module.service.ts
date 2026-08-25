/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// types
import { API_BASE_URL } from "@plane/constants";
import type { IModule, ILinkDetails, ModuleLink, TIssuesResponse } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export class ModuleService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getWorkspaceModules(): Promise<IModule[]> {
    return this.get(`/api/workspace/modules/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getModules(projectId: string): Promise<IModule[]> {
    return this.get(`/api/workspace/projects/${projectId}/modules/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createModule(projectId: string, data: any): Promise<IModule> {
    return this.post(`/api/workspace/projects/${projectId}/modules/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateModule(projectId: string, moduleId: string, data: any): Promise<any> {
    return this.put(`/api/workspace/projects/${projectId}/modules/${moduleId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getModuleDetails(projectId: string, moduleId: string): Promise<IModule> {
    return this.get(`/api/workspace/projects/${projectId}/modules/${moduleId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async patchModule(projectId: string, moduleId: string, data: Partial<IModule>): Promise<IModule> {
    return this.patch(`/api/workspace/projects/${projectId}/modules/${moduleId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteModule(projectId: string, moduleId: string): Promise<any> {
    return this.delete(`/api/workspace/projects/${projectId}/modules/${moduleId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getModuleIssues(projectId: string, moduleId: string, queries?: any, config = {}): Promise<TIssuesResponse> {
    return this.get(
      `/api/workspace/projects/${projectId}/modules/${moduleId}/issues/`,
      {
        params: queries,
      },
      config
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async addIssuesToModule(projectId: string, moduleId: string, data: { issues: string[] }): Promise<void> {
    return this.post(`/api/workspace/projects/${projectId}/modules/${moduleId}/issues/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async addModulesToIssue(
    projectId: string,
    issueId: string,
    data: { modules: string[]; removed_modules?: string[] }
  ): Promise<void> {
    return this.post(`/api/workspace/projects/${projectId}/issues/${issueId}/modules/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async removeIssuesFromModuleBulk(projectId: string, moduleId: string, issueIds: string[]): Promise<void> {
    const promiseDataUrls: any = [];
    issueIds.forEach((issueId) => {
      promiseDataUrls.push(this.delete(`/api/workspace/projects/${projectId}/modules/${moduleId}/issues/${issueId}/`));
    });
    await Promise.all(promiseDataUrls)
      .then((response) => response)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async removeModulesFromIssueBulk(projectId: string, issueId: string, moduleIds: string[]): Promise<void> {
    const promiseDataUrls: any = [];
    moduleIds.forEach((moduleId) => {
      promiseDataUrls.push(this.delete(`/api/workspace/projects/${projectId}/modules/${moduleId}/issues/${issueId}/`));
    });
    await Promise.all(promiseDataUrls)
      .then((response) => response)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createModuleLink(projectId: string, moduleId: string, data: Partial<ModuleLink>): Promise<ILinkDetails> {
    return this.post(`/api/workspace/projects/${projectId}/modules/${moduleId}/module-links/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async updateModuleLink(
    projectId: string,
    moduleId: string,
    linkId: string,
    data: Partial<ModuleLink>
  ): Promise<ILinkDetails> {
    return this.patch(`/api/workspace/projects/${projectId}/modules/${moduleId}/module-links/${linkId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async deleteModuleLink(projectId: string, moduleId: string, linkId: string): Promise<any> {
    return this.delete(`/api/workspace/projects/${projectId}/modules/${moduleId}/module-links/${linkId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async addModuleToFavorites(
    projectId: string,
    data: {
      module: string;
    }
  ): Promise<any> {
    return this.post(`/api/workspace/projects/${projectId}/user-favorite-modules/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async removeModuleFromFavorites(projectId: string, moduleId: string): Promise<any> {
    return this.delete(`/api/workspace/projects/${projectId}/user-favorite-modules/${moduleId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

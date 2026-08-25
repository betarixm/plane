/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  GithubRepositoriesResponse,
  IProjectUserPropertiesResponse,
  ISearchIssueResponse,
  TProjectAnalyticsCount,
  TProjectAnalyticsCountParams,
  TProjectIssuesSearchParams,
} from "@plane/types";
// helpers
// plane web types
import type { TProject, TPartialProject } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export class ProjectService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async createProject(data: Partial<TProject>): Promise<TProject> {
    return this.post(`/api/workspace/projects/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async checkProjectIdentifierAvailability(data: string): Promise<any> {
    return this.get(`/api/workspace/project-identifiers`, {
      params: {
        name: data,
      },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getProjectsLite(): Promise<TPartialProject[]> {
    return this.get(`/api/workspace/projects/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getProjects(): Promise<TProject[]> {
    return this.get(`/api/workspace/projects/details/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getProject(projectId: string): Promise<TProject> {
    return this.get(`/api/workspace/projects/${projectId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response;
      });
  }

  async getProjectAnalyticsCount(params?: TProjectAnalyticsCountParams): Promise<TProjectAnalyticsCount[]> {
    return this.get(`/api/workspace/project-stats/`, {
      params,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateProject(projectId: string, data: Partial<TProject>): Promise<TProject> {
    return this.patch(`/api/workspace/projects/${projectId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteProject(projectId: string): Promise<any> {
    return this.delete(`/api/workspace/projects/${projectId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  // User Properties
  async getProjectUserProperties(projectId: string): Promise<IProjectUserPropertiesResponse> {
    return this.get(`/api/workspace/projects/${projectId}/user-properties/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateProjectUserProperties(
    projectId: string,
    data: Partial<IProjectUserPropertiesResponse>
  ): Promise<IProjectUserPropertiesResponse> {
    return this.patch(`/api/workspace/projects/${projectId}/user-properties/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getGithubRepositories(integrationId: string, page: number): Promise<GithubRepositoriesResponse> {
    return this.get(`/api/workspace/workspace-integrations/${integrationId}/github-repositories/`, {
      params: { page },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async syncGithubRepository(
    projectId: string,
    workspaceIntegrationId: string,
    data: {
      name: string;
      owner: string;
      repository_id: string;
      url: string;
    }
  ): Promise<any> {
    return this.post(
      `/api/workspace/projects/${projectId}/workspace-integrations/${workspaceIntegrationId}/github-repository-sync/`,
      data
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getProjectGithubRepository(projectId: string, integrationId: string): Promise<any> {
    return this.get(
      `/api/workspace/projects/${projectId}/workspace-integrations/${integrationId}/github-repository-sync/`
    )
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getUserProjectFavorites(): Promise<any[]> {
    return this.get(`/api/workspace/user-favorite-projects/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async addProjectToFavorites(project: string): Promise<any> {
    return this.post(`/api/workspace/user-favorite-projects/`, { project })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async removeProjectFromFavorites(projectId: string): Promise<any> {
    return this.delete(`/api/workspace/user-favorite-projects/${projectId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async projectIssuesSearch(projectId: string, params: TProjectIssuesSearchParams): Promise<ISearchIssueResponse[]> {
    return this.get(`/api/workspace/projects/${projectId}/search-issues/`, {
      params,
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}

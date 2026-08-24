/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
// plane imports
import { InstanceWorkspaceService } from "@plane/services";
import type { IWorkspace, TLoader } from "@plane/types";

export interface IWorkspaceStore {
  loader: TLoader;
  workspace: IWorkspace | undefined;
  hydrate: (data: IWorkspace | undefined) => void;
  fetchWorkspace: () => Promise<IWorkspace | undefined>;
}

export class WorkspaceStore implements IWorkspaceStore {
  loader: TLoader = "init-loader";
  workspace: IWorkspace | undefined = undefined;
  private instanceWorkspaceService = new InstanceWorkspaceService();

  constructor() {
    makeObservable(this, {
      loader: observable,
      workspace: observable,
      hydrate: action,
      fetchWorkspace: action,
    });
  }

  hydrate = (data: IWorkspace | undefined) => {
    if (!data) return;
    this.workspace = data;
  };

  fetchWorkspace = async (): Promise<IWorkspace | undefined> => {
    try {
      this.loader = this.workspace ? "mutation" : "init-loader";
      const workspace = await this.instanceWorkspaceService.retrieve();
      runInAction(() => {
        this.workspace = workspace;
      });
      return workspace;
    } catch (error) {
      console.error("Error fetching workspace", error);
      throw error;
    } finally {
      this.loader = "loaded";
    }
  };
}

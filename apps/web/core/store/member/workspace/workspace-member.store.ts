/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { set, sortBy } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// types
import type { EUserPermissions } from "@plane/constants";
import type { IWorkspaceMember } from "@plane/types";
// services
import { WorkspaceService } from "@/services/workspace.service";
// types
import type { IRouterStore } from "@/store/router.store";
import type { IUserStore } from "@/store/user";
// store
import type { IMemberRootStore } from "../index.ts";
import type { IWorkspaceMemberFiltersStore } from "./workspace-member-filters.store";
import { WorkspaceMemberFiltersStore } from "./workspace-member-filters.store";
import type { RootStore } from "@/store/root.store";

export interface IWorkspaceMembership {
  id: string;
  member: string;
  role: EUserPermissions;
  is_active?: boolean;
}

export interface IWorkspaceMemberStore {
  // observables
  workspaceMemberMap: Record<string, Record<string, IWorkspaceMembership>>;
  // filters store
  filtersStore: IWorkspaceMemberFiltersStore;
  // computed
  workspaceMemberIds: string[] | null;
  memberMap: Record<string, IWorkspaceMembership> | null;
  // computed actions
  getWorkspaceMemberIds: (workspaceSlug: string) => string[];
  getFilteredWorkspaceMemberIds: (workspaceSlug: string) => string[];
  getSearchedWorkspaceMemberIds: (searchQuery: string) => string[] | null;
  getWorkspaceMemberDetails: (workspaceMemberId: string) => IWorkspaceMember | null;
  // fetch actions
  fetchWorkspaceMembers: (workspaceSlug: string) => Promise<IWorkspaceMember[]>;
  isUserSuspended: (userId: string, workspaceSlug: string) => boolean;
}

export class WorkspaceMemberStore implements IWorkspaceMemberStore {
  // observables
  workspaceMemberMap: {
    [workspaceSlug: string]: Record<string, IWorkspaceMembership>;
  } = {}; // { workspaceSlug: { userId: userDetails } }
  // filters store
  filtersStore: IWorkspaceMemberFiltersStore;
  // stores
  routerStore: IRouterStore;
  userStore: IUserStore;
  memberRoot: IMemberRootStore;
  // services
  workspaceService;

  constructor(_memberRoot: IMemberRootStore, _rootStore: RootStore) {
    makeObservable(this, {
      // observables
      workspaceMemberMap: observable,
      // computed
      workspaceMemberIds: computed,
      memberMap: computed,
      // actions
      fetchWorkspaceMembers: action,
    });
    // initialize filters store
    this.filtersStore = new WorkspaceMemberFiltersStore();
    // root store
    this.routerStore = _rootStore.router;
    this.userStore = _rootStore.user;
    this.memberRoot = _memberRoot;
    // services
    this.workspaceService = new WorkspaceService();
  }

  /**
   * @description get the list of all the user ids of all the members of the current workspace
   */
  get workspaceMemberIds() {
    const workspaceSlug = this.routerStore.workspaceSlug;
    if (!workspaceSlug) return null;

    return this.getWorkspaceMemberIds(workspaceSlug);
  }

  get memberMap() {
    const workspaceSlug = this.routerStore.workspaceSlug;
    if (!workspaceSlug) return null;
    return this.workspaceMemberMap?.[workspaceSlug] ?? {};
  }

  getWorkspaceMemberIds = computedFn((workspaceSlug: string) => {
    let members = Object.values(this.workspaceMemberMap?.[workspaceSlug] ?? {});
    members = sortBy(members, [
      (m) => m.member !== this.userStore?.data?.id,
      (m) => this.memberRoot?.memberMap?.[m.member]?.display_name?.toLowerCase(),
    ]);
    return members.map((member) => member.member);
  });

  /**
   * @description get the filtered and sorted list of all the user ids of all the members of the workspace
   * @param workspaceSlug
   */
  getFilteredWorkspaceMemberIds = computedFn((workspaceSlug: string) => {
    let members = Object.values(this.workspaceMemberMap?.[workspaceSlug] ?? {});
    // Use filters store to get filtered member ids
    const memberIds = this.filtersStore.getFilteredMemberIds(
      members,
      this.memberRoot?.memberMap || {},
      (member) => member.member
    );

    return memberIds;
  });

  /**
   * @description get the list of all the user ids that match the search query of all the members of the current workspace
   * @param searchQuery
   */
  getSearchedWorkspaceMemberIds = computedFn((searchQuery: string) => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    if (!workspaceSlug) return null;
    const filteredMemberIds = this.getFilteredWorkspaceMemberIds(workspaceSlug);
    if (!filteredMemberIds) return null;
    const searchedWorkspaceMemberIds = filteredMemberIds.filter((userId) => {
      const memberDetails = this.getWorkspaceMemberDetails(userId);
      if (!memberDetails) return false;
      const memberSearchQuery = `${memberDetails.member.first_name} ${memberDetails.member.last_name} ${
        memberDetails.member?.display_name
      } ${memberDetails.member.email ?? ""}`;
      return memberSearchQuery.toLowerCase()?.includes(searchQuery.toLowerCase());
    });
    return searchedWorkspaceMemberIds;
  });

  /**
   * @description get the details of a workspace member
   * @param userId
   */
  getWorkspaceMemberDetails = computedFn((userId: string) => {
    const workspaceSlug = this.routerStore.workspaceSlug;
    if (!workspaceSlug) return null;
    const workspaceMember = this.workspaceMemberMap?.[workspaceSlug]?.[userId];
    if (!workspaceMember) return null;

    const memberDetails: IWorkspaceMember = {
      id: workspaceMember.id,
      role: workspaceMember.role,
      member: this.memberRoot?.memberMap?.[workspaceMember.member],
      is_active: workspaceMember.is_active,
    };
    return memberDetails;
  });

  /**
   * @description fetch all the members of a workspace
   * @param workspaceSlug
   */
  fetchWorkspaceMembers = async (workspaceSlug: string) =>
    await this.workspaceService.fetchWorkspaceMembers(workspaceSlug).then((response) => {
      runInAction(() => {
        response.forEach((member) => {
          set(this.memberRoot?.memberMap, member.member.id, { ...member.member, joining_date: member.created_at });
          set(this.workspaceMemberMap, [workspaceSlug, member.member.id], {
            id: member.id,
            member: member.member.id,
            role: member.role,
            is_active: member.is_active,
          });
        });
      });
      return response;
    });

  isUserSuspended = computedFn((userId: string, workspaceSlug: string) => {
    if (!workspaceSlug) return false;
    const workspaceMember = this.workspaceMemberMap?.[workspaceSlug]?.[userId];
    return workspaceMember?.is_active === false;
  });
}

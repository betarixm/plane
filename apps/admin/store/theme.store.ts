/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, observable, makeObservable } from "mobx";
// root store
import type { RootStore } from "./root.store";

type TTheme = "dark" | "light";
export interface IThemeStore {
  // observables
  theme: string | undefined;
  isSidebarCollapsed: boolean | undefined;
  // actions
  hydrate: (data: any) => void;
  toggleSidebar: (collapsed: boolean) => void;
  setTheme: (currentTheme: TTheme) => void;
}

export class ThemeStore implements IThemeStore {
  // observables
  isSidebarCollapsed: boolean | undefined = undefined;
  theme: string | undefined = undefined;

  constructor(private store: RootStore) {
    makeObservable(this, {
      // observables
      isSidebarCollapsed: observable.ref,
      theme: observable.ref,
      // action
      toggleSidebar: action,
      setTheme: action,
    });
  }

  hydrate = (data: any) => {
    if (data) this.theme = data;
  };

  /**
   * @description Toggle the sidebar collapsed state
   * @param isCollapsed
   */
  toggleSidebar = (isCollapsed: boolean) => {
    if (isCollapsed === undefined) this.isSidebarCollapsed = !this.isSidebarCollapsed;
    else this.isSidebarCollapsed = isCollapsed;
    localStorage.setItem("god_mode_sidebar_collapsed", isCollapsed.toString());
  };

  /**
   * @description Sets the user theme and applies it to the platform
   * @param currentTheme
   */
  setTheme = async (currentTheme: TTheme) => {
    try {
      localStorage.setItem("theme", currentTheme);
      this.theme = currentTheme;
    } catch (error) {
      console.error("setting user theme error", error);
    }
  };
}

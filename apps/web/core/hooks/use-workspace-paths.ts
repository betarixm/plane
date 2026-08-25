/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { usePathname } from "next/navigation";

/**
 * Custom hook to detect different workspace paths
 * @returns Object containing boolean flags for different workspace paths
 */
export const useWorkspacePaths = () => {
  const pathname = usePathname();

  const isAiPath = pathname.startsWith("/pi-chat");
  const isSettingsPath = pathname.startsWith("/settings") && !pathname.startsWith("/settings/profile");
  const isProjectsPath =
    /^\/(active-cycles|analytics|browse|drafts|notifications|profile|projects|stickies|workspace-views)(\/|$)/.test(
      pathname
    );
  const isNotificationsPath = pathname.startsWith("/notifications");

  return {
    isSettingsPath,
    isAiPath,
    isProjectsPath,
    isNotificationsPath,
  };
};

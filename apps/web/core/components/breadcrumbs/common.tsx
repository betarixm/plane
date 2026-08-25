/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// local components
import { useProjectNavigationPreferences } from "@/hooks/use-navigation-preferences";
import { ProjectBreadcrumb } from "./project";

type TCommonProjectBreadcrumbProps = {
  projectId: string;
};

export function CommonProjectBreadcrumbs(props: TCommonProjectBreadcrumbProps) {
  const { projectId } = props;
  // preferences
  const { preferences: projectPreferences } = useProjectNavigationPreferences();

  if (projectPreferences.navigationMode === "TABBED") return null;
  return <ProjectBreadcrumb projectId={projectId} />;
}

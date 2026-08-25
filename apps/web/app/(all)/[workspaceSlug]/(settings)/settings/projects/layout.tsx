/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { Outlet } from "react-router";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useAppRouter } from "@/hooks/use-app-router";
// types
import type { Route } from "./+types/layout";

function ProjectSettingsLayout({ params }: Route.ComponentProps) {
  const { projectId } = params;
  // router
  const router = useAppRouter();
  // store hooks
  const { joinedProjectIds } = useProject();

  useEffect(() => {
    if (projectId) return;
    if (joinedProjectIds.length > 0) {
      router.push(`/settings/projects/${joinedProjectIds[0]}`);
    }
  }, [joinedProjectIds, router, projectId]);

  return <Outlet />;
}

export default observer(ProjectSettingsLayout);

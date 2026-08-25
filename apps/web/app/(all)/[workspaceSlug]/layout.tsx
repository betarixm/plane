/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Outlet } from "react-router";
import { useParams } from "next/navigation";
import { AuthenticationWrapper } from "@/lib/wrappers/authentication-wrapper";
import { WorkspaceContentWrapper } from "@/components/workspace/content-wrapper";
import { AppRailVisibilityProvider } from "@/lib/app-rail";
import { GlobalModals } from "@/components/common/modal/global";
import { WorkspaceAuthWrapper } from "@/layouts/auth-layout/workspace-wrapper";

function WorkspaceLayout() {
  const { workspaceSlug } = useParams();

  return (
    <AuthenticationWrapper>
      <WorkspaceAuthWrapper>
        <AppRailVisibilityProvider>
          <WorkspaceContentWrapper>
            {workspaceSlug && <GlobalModals workspaceSlug={workspaceSlug} />}
            <Outlet />
          </WorkspaceContentWrapper>
        </AppRailVisibilityProvider>
      </WorkspaceAuthWrapper>
    </AuthenticationWrapper>
  );
}

export default observer(WorkspaceLayout);

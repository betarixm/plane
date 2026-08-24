/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
import { Loader as LoaderIcon } from "lucide-react";
// plane imports
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { WorkspaceListItem } from "@/components/workspace/list-item";
// hooks
import { useWorkspace } from "@/hooks/store";
// types
import type { Route } from "./+types/page";

const WorkspaceManagementPage = observer(function WorkspaceManagementPage(_props: Route.ComponentProps) {
  const { workspace, loader: workspaceLoader, fetchWorkspace } = useWorkspace();

  useSWR("INSTANCE_WORKSPACE", () => fetchWorkspace());

  return (
    <PageWrapper
      header={{
        title: "Workspace",
        description: "View the workspace connected to this instance.",
      }}
    >
      {workspaceLoader !== "init-loader" ? (
        <div className="space-y-4 py-2">
          <div className="flex items-center gap-2 text-16 font-medium">
            Instance workspace
            {workspaceLoader === "mutation" && <LoaderIcon className="h-4 w-4 animate-spin" />}
          </div>
          {workspace ? (
            <WorkspaceListItem />
          ) : (
            <div className="rounded-lg border border-subtle bg-layer-1 p-4 text-13 text-tertiary">
              The workspace has not been initialized yet.
            </div>
          )}
        </div>
      ) : (
        <Loader className="space-y-10 py-8">
          <Loader.Item height="24px" width="20%" />
          <Loader.Item height="92px" width="100%" />
        </Loader>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "Workspace - Administration" }];

export default WorkspaceManagementPage;

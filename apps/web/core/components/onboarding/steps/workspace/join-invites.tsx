/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
// plane imports
import { ROLE } from "@plane/constants";
import { Button } from "@plane/propel/button";
import type { IWorkspaceMemberInvitationPublic } from "@plane/types";
import { Spinner } from "@plane/ui";
// components
import { WorkspaceLogo } from "@/components/workspace/logo";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserSettings } from "@/hooks/store/user";
// services
import { WorkspaceService } from "@/services/workspace.service";
// local components
import { CommonOnboardingHeader } from "../common";

type Props = {
  invitation?: IWorkspaceMemberInvitationPublic;
  handleNextStep: () => Promise<void>;
};

const workspaceService = new WorkspaceService();

export function WorkspaceJoinInvitationStep({ invitation, handleNextStep }: Props) {
  const [isJoiningWorkspace, setIsJoiningWorkspace] = useState(false);
  const { fetchWorkspace } = useWorkspace();
  const { fetchCurrentUserSettings } = useUserSettings();
  const acceptInvitation = async () => {
    if (!invitation) return;
    setIsJoiningWorkspace(true);

    try {
      await workspaceService.acceptWorkspaceInvitation();
      await fetchWorkspace();
      await fetchCurrentUserSettings();
      await handleNextStep();
    } catch (error) {
      console.error(error);
      setIsJoiningWorkspace(false);
    }
  };

  if (!invitation) {
    return (
      <div className="flex flex-col gap-10">
        <CommonOnboardingHeader
          title="Invitation required"
          description="Ask an administrator to invite you to this workspace, then return here to continue."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-10">
      <CommonOnboardingHeader title="Join your workspace" description="Accept the invitation to get started." />
      <div className="flex items-center gap-2 rounded-lg border border-subtle px-3 py-2">
        <WorkspaceLogo
          logo={invitation.workspace.logo_url}
          name={invitation.workspace.name}
          classNames="size-8 shrink-0 rounded-lg"
        />
        <div className="min-w-0 flex-1">
          <div className="truncate text-13 font-medium">{invitation.workspace.name}</div>
          <p className="text-11 text-secondary">{ROLE[invitation.role]}</p>
        </div>
      </div>
      <Button variant="primary" size="xl" className="w-full" onClick={acceptInvitation} disabled={isJoiningWorkspace}>
        {isJoiningWorkspace ? <Spinner height="20px" width="20px" /> : "Accept invitation"}
      </Button>
    </div>
  );
}

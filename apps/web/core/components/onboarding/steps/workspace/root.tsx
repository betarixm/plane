/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IWorkspaceMemberInvitationPublic } from "@plane/types";
import { EOnboardingSteps } from "@plane/types";
// local components
import { WorkspaceJoinInvitationStep } from "./join-invites";

type Props = {
  invitation?: IWorkspaceMemberInvitationPublic;
  handleStepChange: (step: EOnboardingSteps) => void;
};

export function WorkspaceSetupStep({ invitation, handleStepChange }: Props) {
  return (
    <WorkspaceJoinInvitationStep
      invitation={invitation}
      handleNextStep={async () => handleStepChange(EOnboardingSteps.WORKSPACE_JOIN)}
    />
  );
}

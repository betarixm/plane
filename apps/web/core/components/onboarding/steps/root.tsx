/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";
// plane imports
import type { IWorkspaceMemberInvitationPublic } from "@plane/types";
import { EOnboardingSteps } from "@plane/types";
// local components
import { ProfileSetupStep } from "./profile";
import { RoleSetupStep } from "./role";
import { UseCaseSetupStep } from "./usecase";
import { WorkspaceSetupStep } from "./workspace";

type Props = {
  currentStep: EOnboardingSteps;
  invitation?: IWorkspaceMemberInvitationPublic;
  handleStepChange: (step: EOnboardingSteps, skipInvites?: boolean) => void;
};

function OnboardingStepContent({ currentStep, invitation, handleStepChange }: Props) {
  switch (currentStep) {
    case EOnboardingSteps.PROFILE_SETUP:
      return <ProfileSetupStep handleStepChange={handleStepChange} />;
    case EOnboardingSteps.ROLE_SETUP:
      return <RoleSetupStep handleStepChange={handleStepChange} />;
    case EOnboardingSteps.USE_CASE_SETUP:
      return <UseCaseSetupStep handleStepChange={handleStepChange} />;
    case EOnboardingSteps.WORKSPACE_JOIN:
      return <WorkspaceSetupStep invitation={invitation} handleStepChange={handleStepChange} />;
    default:
      return null;
  }
}

export function OnboardingStepRoot(props: Props) {
  const { currentStep } = props;
  // ref for the scrollable container
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // scroll to top when step changes
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    }
  }, [currentStep]);

  return (
    <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-8">
        <div className="w-full max-w-[24rem]">
          <OnboardingStepContent {...props} />
        </div>
      </div>
    </div>
  );
}

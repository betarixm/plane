/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR, { mutate } from "swr";
// plane imports
import { ROLE, USER_WORKSPACE } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { PlaneLogo } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// assets
import emptyInvitation from "@/app/assets/empty-state/invitation.svg?url";
// components
import { EmptyState } from "@/components/common/empty-state";
import { WorkspaceLogo } from "@/components/workspace/logo";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUser } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
// wrappers and services
import { AuthenticationWrapper } from "@/lib/wrappers/authentication-wrapper";
import { WorkspaceService } from "@/services/workspace.service";

const workspaceService = new WorkspaceService();

function UserInvitationsPage() {
  const [isJoiningWorkspace, setIsJoiningWorkspace] = useState(false);
  const router = useAppRouter();
  const { t } = useTranslation();
  const { data: currentUser } = useUser();
  const { fetchWorkspace } = useWorkspace();
  const { data: invitation, isLoading } = useSWR("USER_WORKSPACE_INVITATION", () =>
    workspaceService.userWorkspaceInvitation()
  );

  const acceptInvitation = async () => {
    if (!invitation) return;
    setIsJoiningWorkspace(true);

    try {
      await workspaceService.acceptWorkspaceInvitation();
      await mutate(USER_WORKSPACE);
      await fetchWorkspace();
      router.push(`/${invitation.workspace.slug}`);
    } catch (_error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("error"),
        message: t("something_went_wrong_please_try_again"),
      });
      setIsJoiningWorkspace(false);
    }
  };

  return (
    <AuthenticationWrapper>
      <div className="flex h-full flex-col gap-y-2 overflow-hidden sm:flex-row sm:gap-y-0">
        <div className="relative h-1/6 flex-shrink-0 sm:w-2/12 md:w-3/12 lg:w-1/5">
          <div className="absolute top-1/2 left-0 h-[0.5px] w-full -translate-y-1/2 border-b-[0.5px] border-subtle sm:top-0 sm:left-1/2 sm:h-screen sm:w-[0.5px] sm:-translate-x-1/2 sm:translate-y-0 sm:border-r-[0.5px] md:left-1/3" />
          <Link
            href="/"
            className="absolute top-1/2 left-5 z-10 grid -translate-y-1/2 place-items-center px-3 sm:top-12 sm:left-1/2 sm:-translate-x-[15px] sm:translate-y-0 sm:px-0 sm:py-5 md:left-1/3"
          >
            <PlaneLogo className="h-9 w-auto text-primary" />
          </Link>
          <div className="absolute top-1/4 right-4 -translate-y-1/2 text-13 text-primary sm:fixed sm:top-12 sm:right-16 sm:translate-y-0 sm:py-5">
            {currentUser?.email}
          </div>
        </div>
        {!isLoading ? (
          invitation ? (
            <div className="relative flex h-full justify-center px-8 pb-8 sm:w-10/12 sm:items-center sm:justify-start sm:p-0 sm:pr-[8.33%] md:w-9/12 lg:w-4/5">
              <div className="w-full space-y-10 md:w-3/5">
                <div className="space-y-2">
                  <h4 className="text-20 font-semibold">Join your workspace</h4>
                  <p className="text-13 text-secondary">Accept the invitation to start collaborating.</p>
                </div>
                <div className="flex items-center gap-2 rounded-sm border border-subtle px-3.5 py-5">
                  <WorkspaceLogo
                    logo={invitation.workspace.logo_url}
                    name={invitation.workspace.name}
                    classNames="size-9 shrink-0"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-13 font-medium">{invitation.workspace.name}</div>
                    <p className="text-11 text-secondary">{ROLE[invitation.role]}</p>
                  </div>
                </div>
                <Button
                  variant="primary"
                  type="button"
                  size="lg"
                  onClick={acceptInvitation}
                  disabled={isJoiningWorkspace}
                  loading={isJoiningWorkspace}
                >
                  {t("accept_and_join")}
                </Button>
              </div>
            </div>
          ) : (
            <div className="fixed top-0 left-0 grid h-full w-full place-items-center">
              <EmptyState
                title={t("no_pending_invites")}
                description="Ask an administrator to invite you to this workspace."
                image={emptyInvitation}
              />
            </div>
          )
        ) : null}
      </div>
    </AuthenticationWrapper>
  );
}

export default observer(UserInvitationsPage);

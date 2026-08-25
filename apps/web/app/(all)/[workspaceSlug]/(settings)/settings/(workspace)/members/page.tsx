/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { MessageSquare } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel, getIdentitySourceDescriptor } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { SearchIcon } from "@plane/propel/icons";
import { cn } from "@plane/utils";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { CountChip } from "@/components/common/count-chip";
import { PageHead } from "@/components/core/page-title";
import { MemberListFiltersDropdown } from "@/components/project/dropdowns/filters/member-list";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { WorkspaceMembersList } from "@/components/workspace/settings/members-list";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
import { useMember } from "@/hooks/store/use-member";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import type { Route } from "./+types/page";
import { MembersWorkspaceSettingsHeader } from "./header";

const WorkspaceMembersSettingsPage = observer(function WorkspaceMembersSettingsPage(_props: Route.ComponentProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { config } = useInstance();
  const {
    workspace: { workspaceMemberIds, filtersStore },
  } = useMember();
  const { currentWorkspace } = useWorkspace();
  const { t } = useTranslation();
  const identitySource = config?.identity_source;
  const descriptor = identitySource ? getIdentitySourceDescriptor(identitySource.provider) : undefined;

  const canViewWorkspaceMembers = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.WORKSPACE
  );
  const appliedRoleFilters = filtersStore.filters?.roles || [];
  const pageTitle = currentWorkspace?.name ? `${currentWorkspace.name} - Members` : undefined;

  const handleRoleFilterUpdate = (role: string) => {
    const currentRoles = filtersStore.filters?.roles || [];
    const updatedRoles = currentRoles.includes(role)
      ? currentRoles.filter((item) => item !== role)
      : [...currentRoles, role];
    filtersStore.updateFilters({ roles: updatedRoles.length > 0 ? updatedRoles : undefined });
  };

  if (workspaceUserInfo && !canViewWorkspaceMembers) {
    return <NotAuthorizedView section="settings" className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<MembersWorkspaceSettingsHeader />} hugging>
      <PageHead title={pageTitle} />
      <section className={cn("size-full", { "opacity-60": !canViewWorkspaceMembers })}>
        <div className="flex flex-wrap items-center justify-between gap-4 pb-3.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h4 className="flex items-center gap-2.5 text-h3-medium">
              {t("workspace_settings.settings.members.title")}
              {!!workspaceMemberIds?.length && <CountChip count={workspaceMemberIds.length} className="m-auto h-5" />}
            </h4>
            <div className="flex items-center gap-1.5 rounded-full bg-layer-1 px-2.5 py-1 text-caption-sm-medium text-tertiary">
              <MessageSquare className="size-3.5" />
              Synced from {descriptor?.label ?? "identity source"}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 rounded-md border border-subtle bg-surface-1 px-2.5 py-1.5">
              <SearchIcon className="h-3.5 w-3.5 text-placeholder" />
              <input
                className="w-full max-w-[234px] border-none bg-transparent text-body-xs-regular outline-none placeholder:text-placeholder"
                placeholder={`${t("search")}...`}
                value={searchQuery}
                // eslint-disable-next-line jsx-a11y/no-autofocus
                autoFocus
                onChange={(event) => setSearchQuery(event.target.value)}
              />
            </div>
            <MemberListFiltersDropdown
              appliedFilters={appliedRoleFilters}
              handleUpdate={handleRoleFilterUpdate}
              memberType="workspace"
            />
          </div>
        </div>
        <p className="mb-5 text-body-xs-regular text-tertiary">
          Join, leave, and profile changes are managed in {descriptor?.label ?? "your identity source"} and synchronized
          automatically.
        </p>
        <WorkspaceMembersList searchQuery={searchQuery} />
      </section>
    </SettingsContentWrapper>
  );
});

export default WorkspaceMembersSettingsPage;

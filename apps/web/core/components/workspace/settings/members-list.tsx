/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
// components
import { MembersSettingsLoader } from "@/components/ui/loader/settings/members";
// hooks
import { useMember } from "@/hooks/store/use-member";
// local imports
import { WorkspaceMembersListItem } from "./members-list-item";

export const WorkspaceMembersList = observer(function WorkspaceMembersList({ searchQuery }: { searchQuery: string }) {
  const { workspaceSlug } = useParams();
  const {
    workspace: {
      fetchWorkspaceMembers,
      workspaceMemberIds,
      getFilteredWorkspaceMemberIds,
      getSearchedWorkspaceMemberIds,
      getWorkspaceMemberDetails,
    },
  } = useMember();
  const { t } = useTranslation();

  useSWR(
    workspaceSlug ? `WORKSPACE_MEMBERS_${workspaceSlug.toString()}` : null,
    workspaceSlug ? () => fetchWorkspaceMembers(workspaceSlug.toString()) : null
  );

  if (!workspaceMemberIds) return <MembersSettingsLoader />;

  const filteredMemberIds = workspaceSlug ? getFilteredWorkspaceMemberIds(workspaceSlug.toString()) : [];
  const searchedMemberIds = searchQuery ? getSearchedWorkspaceMemberIds(searchQuery) : filteredMemberIds;
  const memberDetails = searchedMemberIds?.map((memberId) => getWorkspaceMemberDetails(memberId));
  const orderedMemberDetails = memberDetails
    ? [...memberDetails.filter((member) => member?.is_active), ...memberDetails.filter((member) => !member?.is_active)]
    : [];

  return (
    <div className="divide-y-[0.5px] divide-subtle overflow-scroll">
      {!!searchedMemberIds?.length && <WorkspaceMembersListItem memberDetails={orderedMemberDetails} />}
      {searchedMemberIds?.length === 0 && (
        <h4 className="mt-16 text-center text-body-xs-regular text-placeholder">{t("no_matching_members")}</h4>
      )}
    </div>
  );
});

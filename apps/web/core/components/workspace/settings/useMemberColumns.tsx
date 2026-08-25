/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
// plane imports
import { getIdentitySourceDescriptor } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { renderFormattedDate } from "@plane/utils";
// components
import { MemberHeaderColumn } from "@/components/project/member-header-column";
import type { RowData } from "@/components/workspace/settings/member-columns";
import { AccountTypeColumn, NameColumn } from "@/components/workspace/settings/member-columns";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
import { useMember } from "@/hooks/store/use-member";
import type { IMemberFilters } from "@/store/member/utils";

const isSuspended = (rowData: RowData) => rowData.is_active === false;

export const useMemberColumns = () => {
  const { workspaceSlug } = useParams();
  const { config } = useInstance();
  const {
    workspace: {
      filtersStore: { filters, updateFilters },
    },
  } = useMember();
  const { t } = useTranslation();
  const identitySource = config?.identity_source;
  const descriptor = identitySource ? getIdentitySourceDescriptor(identitySource.provider) : undefined;

  const handleDisplayFilterUpdate = (filterUpdates: Partial<IMemberFilters>) => updateFilters(filterUpdates);

  const columns = [
    {
      key: "Name",
      content: t("workspace_settings.settings.members.details.display_name"),
      thClassName: "text-left",
      thRender: () => (
        <MemberHeaderColumn
          property="display_name"
          displayFilters={filters}
          handleDisplayFilterUpdate={handleDisplayFilterUpdate}
        />
      ),
      tdRender: (rowData: RowData) => <NameColumn rowData={rowData} workspaceSlug={workspaceSlug.toString()} />,
    },
    {
      key: "Email address",
      content: t("workspace_settings.settings.members.details.email_address"),
      tdRender: (rowData: RowData) => (
        <div className={`w-48 truncate ${isSuspended(rowData) ? "text-placeholder" : ""}`}>{rowData.member.email}</div>
      ),
      thRender: () => (
        <MemberHeaderColumn
          property="email"
          displayFilters={filters}
          handleDisplayFilterUpdate={handleDisplayFilterUpdate}
        />
      ),
    },
    {
      key: "Account type",
      content: t("workspace_settings.settings.members.details.account_type"),
      thRender: () => (
        <MemberHeaderColumn
          property="role"
          displayFilters={filters}
          handleDisplayFilterUpdate={handleDisplayFilterUpdate}
        />
      ),
      tdRender: (rowData: RowData) => <AccountTypeColumn rowData={rowData} />,
    },
    {
      key: "Authentication",
      content: t("workspace_settings.settings.members.details.authentication"),
      tdRender: (rowData: RowData) =>
        isSuspended(rowData) ? null : <div>{descriptor?.label ?? "External identity source"}</div>,
    },
    {
      key: "Joining date",
      content: t("workspace_settings.settings.members.details.joining_date"),
      tdRender: (rowData: RowData) =>
        isSuspended(rowData) ? null : <div>{renderFormattedDate(rowData.member.joining_date)}</div>,
      thRender: () => (
        <MemberHeaderColumn
          property="joining_date"
          displayFilters={filters}
          handleDisplayFilterUpdate={handleDisplayFilterUpdate}
        />
      ),
    },
  ];

  return { columns };
};

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isEmpty } from "lodash-es";
// plane imports
import type { IWorkspaceMember } from "@plane/types";
import { Table } from "@plane/ui";
// components
import { MembersLayoutLoader } from "@/components/ui/loader/layouts/members-layout-loader";
import type { RowData } from "@/components/workspace/settings/member-columns";
import { useMemberColumns } from "@/components/workspace/settings/useMemberColumns";

type Props = {
  memberDetails: (IWorkspaceMember | null)[];
};

export function WorkspaceMembersListItem({ memberDetails }: Props) {
  const { columns } = useMemberColumns();

  if (isEmpty(columns)) return <MembersLayoutLoader />;

  return (
    <div className="grid border-t border-subtle">
      <Table<RowData>
        columns={columns}
        data={memberDetails.filter((member): member is IWorkspaceMember => member !== null)}
        keyExtractor={(rowData) => rowData.member.id}
        tHeadClassName="border-b border-subtle"
        thClassName="text-left font-medium divide-x-0 text-placeholder"
        tBodyClassName="divide-y-0"
        tBodyTrClassName="divide-x-0 p-4 h-10 text-secondary"
        tHeadTrClassName="divide-x-0"
      />
    </div>
  );
}

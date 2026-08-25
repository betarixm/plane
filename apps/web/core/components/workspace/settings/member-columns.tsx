/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
// plane imports
import { ROLE } from "@plane/constants";
import { SuspendedUserIcon } from "@plane/propel/icons";
import { Pill, EPillVariant, EPillSize } from "@plane/propel/pill";
import type { IWorkspaceMember } from "@plane/types";
import { getFileURL } from "@plane/utils";

export type RowData = IWorkspaceMember;

export function NameColumn({ rowData, workspaceSlug }: { rowData: RowData; workspaceSlug: string }) {
  const { avatar_url, display_name, id } = rowData.member;
  const isSuspended = rowData.is_active === false;

  return (
    <div className="flex w-72 items-center gap-2">
      {isSuspended ? (
        <div className="rounded-full bg-layer-1">
          <SuspendedUserIcon className="size-6 text-placeholder" />
        </div>
      ) : (
        <Link href={`/${workspaceSlug}/profile/${id}`}>
          {avatar_url?.trim() ? (
            <span className="relative flex size-6 items-center justify-center rounded-full text-on-color capitalize">
              <img
                src={getFileURL(avatar_url)}
                className="absolute top-0 left-0 size-full rounded-full object-cover"
                alt={display_name || undefined}
              />
            </span>
          ) : (
            <span className="relative flex size-6 items-center justify-center rounded-full bg-layer-3 text-11 text-tertiary capitalize">
              {(display_name || "?")[0]}
            </span>
          )}
        </Link>
      )}
      <span className={isSuspended ? "text-placeholder" : ""}>{display_name}</span>
    </div>
  );
}

export function AccountTypeColumn({ rowData }: { rowData: RowData }) {
  if (rowData.is_active === false) {
    return (
      <div className="flex w-32">
        <Pill variant={EPillVariant.DEFAULT} size={EPillSize.SM} className="border-none">
          Suspended
        </Pill>
      </div>
    );
  }

  return <div className="flex w-32">{ROLE[rowData.role]}</div>;
}

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { CircleUserRound, MessageSquare } from "lucide-react";
// plane imports
import { getIdentitySourceDescriptor } from "@plane/constants";
import type { IUser } from "@plane/types";
import { getFileURL } from "@plane/utils";
// hooks
import { useInstance } from "@/hooks/store/use-instance";

type Props = {
  user: IUser;
};

export function GeneralProfileSettingsForm({ user }: Props) {
  const { config } = useInstance();
  const identitySource = config?.identity_source;
  const descriptor = identitySource ? getIdentitySourceDescriptor(identitySource.provider) : undefined;

  return (
    <div className="flex w-full flex-col gap-7">
      <div className="flex items-start gap-3 rounded-lg border border-subtle bg-layer-1 p-4">
        <MessageSquare className="size-8 shrink-0 text-secondary" />
        <div className="flex flex-col gap-1">
          <h3 className="text-body-sm-medium text-primary">Managed by {descriptor?.label ?? "your identity source"}</h3>
          <p className="text-body-xs-regular text-tertiary">
            Your name, email, and profile picture are synchronized from your {descriptor?.label ?? "external"} profile
            and cannot be edited here.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4 border-b border-subtle pb-7">
        {user.avatar_url ? (
          <img
            src={getFileURL(user.avatar_url)}
            className="size-16 rounded-lg object-cover"
            alt={user.display_name || undefined}
          />
        ) : (
          <div className="flex size-16 items-center justify-center rounded-lg bg-layer-1">
            <CircleUserRound className="size-10 text-secondary" />
          </div>
        )}
        <div className="min-w-0">
          <h2 className="truncate text-h4-medium text-primary">{user.display_name}</h2>
          <p className="truncate text-body-xs-regular text-tertiary">{user.email}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <ReadOnlyProfileField label="Name" value={user.display_name} />
        <ReadOnlyProfileField label="Email" value={user.email} />
      </div>
    </div>
  );
}

function ReadOnlyProfileField({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-body-xs-medium text-secondary">{label}</span>
      <div className="min-h-9 rounded-md border border-subtle bg-surface-2 px-3 py-2 text-body-xs-regular text-tertiary">
        {value || "—"}
      </div>
    </div>
  );
}

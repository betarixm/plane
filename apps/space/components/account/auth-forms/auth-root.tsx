/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useSearchParams } from "next/navigation";
import { MessageSquare } from "lucide-react";
// plane imports
import { API_BASE_URL, getIdentitySourceDescriptor, getIdentitySourceSignInError } from "@plane/constants";
import { Banner } from "@plane/propel/banner";
import { getButtonStyling } from "@plane/propel/button";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
// local imports
import { TermsAndConditions } from "../terms-and-conditions";
import { AuthHeader } from "./auth-header";

const getApiUrl = (path: string): string => (/^https?:\/\//.test(path) ? path : `${API_BASE_URL}${path}`);

export const AuthRoot = observer(function AuthRoot() {
  const searchParams = useSearchParams();
  const { config } = useInstance();
  const identitySource = config?.identity_source;
  const descriptor = identitySource ? getIdentitySourceDescriptor(identitySource.provider) : undefined;
  const nextPath = searchParams.get("next_path") || "/";
  const errorName = searchParams.get("error_message");
  const errorMessage = identitySource ? getIdentitySourceSignInError(identitySource.provider, errorName) : undefined;
  const query = new URLSearchParams({ origin: "space", next_path: nextPath }).toString();
  const requiresReconnect = identitySource?.connected === false;
  const authenticationPath = requiresReconnect ? identitySource?.install_url : identitySource?.auth_url;
  const authenticationUrl = authenticationPath
    ? getApiUrl(`${authenticationPath}${authenticationPath.includes("?") ? "&" : "?"}${query}`)
    : undefined;

  return (
    <div className="mt-10 flex w-full flex-grow flex-col items-center justify-center py-6">
      <div className="relative flex w-full max-w-[22.5rem] flex-col gap-6">
        <AuthHeader />
        {errorMessage && <Banner variant="error" title={errorMessage} role="alert" />}
        {identitySource?.configured && authenticationUrl && descriptor ? (
          <a
            href={authenticationUrl}
            className={`${getButtonStyling("primary", "xl")} flex w-full items-center justify-center gap-2`}
          >
            <MessageSquare className="size-4" />
            {requiresReconnect
              ? `Reconnect ${descriptor.label} (${descriptor.label} admins only)`
              : `Continue with ${descriptor.label}`}
          </a>
        ) : descriptor ? (
          <Banner variant="warning" title={descriptor.serverConfigurationHint} role="alert" />
        ) : null}
        {descriptor && (
          <p className="text-center text-11 leading-5 text-tertiary">
            Your {descriptor.label} {descriptor.organizationLabel} manages your account, profile, and membership.
          </p>
        )}
        <TermsAndConditions />
      </div>
    </div>
  );
});

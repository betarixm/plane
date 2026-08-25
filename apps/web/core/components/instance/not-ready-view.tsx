/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL, getIdentitySourceDescriptor } from "@plane/constants";
import type { IIdentitySourceConfig } from "@plane/types";
// assets
import GradientLogo from "@/app/assets/auth/gradient-logo.webp?url";
import GradientBgLogo from "@/app/assets/auth/gradient-bg-logo.webp?url";
import DefaultLayout from "@/layouts/default-layout";
import { PlaneLockup } from "@plane/propel/icons";
import { Button } from "@plane/propel/button";

type TInstanceNotReadyProps = {
  identitySource: IIdentitySourceConfig | undefined;
};

const getApiUrl = (path: string): string => (/^https?:\/\//.test(path) ? path : `${API_BASE_URL}${path}`);

export function InstanceNotReady({ identitySource }: TInstanceNotReadyProps) {
  const descriptor = identitySource ? getIdentitySourceDescriptor(identitySource.provider) : undefined;
  return (
    <DefaultLayout>
      <div className="relative z-10 flex h-screen w-screen overflow-hidden">
        {/* Background decorations */}
        <img
          src={GradientBgLogo}
          className="pointer-events-none absolute -top-24 -left-32 h-56 w-96 opacity-15"
          alt=""
          aria-hidden="true"
        />
        <img
          src={GradientBgLogo}
          className="pointer-events-none absolute -right-20 -bottom-16 h-56 w-96 opacity-15"
          alt=""
          aria-hidden="true"
        />
        {/* Main content */}
        <div className="flex h-full w-full flex-col items-center px-8 pt-6 pb-10">
          <div className="sticky top-0 flex w-full shrink-0 items-center justify-between gap-6">
            <PlaneLockup height={20} width={95} className="text-primary" />
          </div>
          <div className="flex h-full w-full flex-col items-center justify-center gap-7">
            <div className="flex flex-col items-center gap-11">
              <img src={GradientLogo} className="h-24 w-40 object-contain" alt="Plane Logo" />
              <div className="flex max-w-124 flex-col items-center gap-3">
                <h1 className="text-h2-semibold text-primary">Welcome to Plane</h1>
                <p className="text-center text-body-md-regular text-secondary">
                  {descriptor
                    ? `Connect the ${descriptor.label} ${descriptor.organizationLabel} that will own Plane identities, profiles, and membership.`
                    : "Configure an identity source to own Plane identities, profiles, and membership."}
                </p>
              </div>
            </div>
            {identitySource?.configured && descriptor ? (
              <a href={getApiUrl(identitySource.install_url)} className="w-72">
                <Button variant="primary" className="w-full" size="xl">
                  Connect {descriptor.label}
                </Button>
              </a>
            ) : descriptor ? (
              <p className="max-w-lg text-center text-body-sm-regular text-secondary">
                {descriptor.serverConfigurationHint}
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </DefaultLayout>
  );
}

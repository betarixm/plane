/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { WEB_URL } from "@plane/constants";
import { getButtonStyling } from "@plane/propel/button";
import { AuthHeader } from "./auth-header";
import { FormHeader } from "@/components/instance/form-header";

export function AdministrationEntry() {
  return (
    <>
      <AuthHeader />
      <div className="mt-10 flex w-full flex-grow flex-col items-center justify-center py-6">
        <div className="flex w-full max-w-[22.5rem] flex-col gap-6">
          <FormHeader
            heading="Workspace administration"
            subHeading="Administration uses the same account and session as your workspace."
          />
          <a href={WEB_URL || "/"} className={getButtonStyling("primary", "xl")}>
            Continue to Plane
          </a>
        </div>
      </div>
    </>
  );
}

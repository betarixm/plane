/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import Link from "next/link";
import { PlaneLockup } from "@plane/propel/icons";
import { PageHead } from "@/components/core/page-title";
export function AuthHeader() {
  return <AuthHeaderBase pageTitle="Sign in" />;
}

type TAuthHeaderBase = {
  pageTitle: string;
  additionalAction?: React.ReactNode;
};

export function AuthHeaderBase(props: TAuthHeaderBase) {
  const { pageTitle, additionalAction } = props;
  return (
    <>
      <PageHead title={pageTitle + " - Plane"} />
      <div className="sticky top-0 flex w-full flex-shrink-0 items-center justify-between gap-6">
        <Link href="/">
          <PlaneLockup height={20} width={95} className="text-primary" />
        </Link>
        {additionalAction}
      </div>
    </>
  );
}

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// hooks
import { useInstance } from "@/hooks/store";
// local imports
import { GeneralConfigurationForm } from "./form";
// types
import type { Route } from "./+types/page";

function GeneralPage() {
  const { instance } = useInstance();

  return (
    <PageWrapper
      header={{
        title: "General settings",
        description: "Change the name of your instance and enable or disable telemetry.",
      }}
    >
      {instance && <GeneralConfigurationForm instance={instance} />}
    </PageWrapper>
  );
}

export const meta: Route.MetaFunction = () => [{ title: "General Settings - Administration" }];

export default observer(GeneralPage);

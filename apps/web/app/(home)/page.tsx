/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
// components
import { AuthBase } from "@/components/auth-screens/auth-base";
// layouts
import DefaultLayout from "@/layouts/default-layout";
// wrappers
import { AuthenticationWrapper } from "@/lib/wrappers/authentication-wrapper";

function HomePage() {
  return (
    <DefaultLayout>
      <AuthenticationWrapper mode="guest">
        <AuthBase />
      </AuthenticationWrapper>
    </DefaultLayout>
  );
}

export default HomePage;

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { ICsrfTokenData } from "@plane/types";
import { APIService } from "../api.service";

export class AuthService extends APIService {
  constructor(baseUrl?: string) {
    super(baseUrl || API_BASE_URL);
  }

  async requestCSRFToken(): Promise<ICsrfTokenData> {
    return this.get("/auth/get-csrf-token/", { validateStatus: null })
      .then((response) => response.data)
      .catch((error) => {
        throw error;
      });
  }

  async signOut(baseUrl: string): Promise<void> {
    const { csrf_token: csrfToken } = await this.requestCSRFToken();
    if (!csrfToken) throw new Error("CSRF token not found");

    const form = document.createElement("form");
    const csrfInput = document.createElement("input");

    form.method = "POST";
    form.action = `${baseUrl}/auth/sign-out/`;
    csrfInput.value = csrfToken;
    csrfInput.name = "csrfmiddlewaretoken";
    csrfInput.type = "hidden";
    form.appendChild(csrfInput);
    document.body.appendChild(form);
    form.submit();
  }
}

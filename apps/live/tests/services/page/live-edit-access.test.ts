/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { AxiosResponse } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/env", () => ({
  env: {
    API_BASE_URL: "http://api.example.test",
  },
}));

vi.mock("@plane/logger", () => ({
  logger: {
    error: vi.fn(),
  },
}));

import { PageCoreService } from "@/services/page/core.service";
import { LIVE_AUTHORIZATION_REQUEST_TIMEOUT_MS } from "@/lib/live-authorization-constants";

class TestPageService extends PageCoreService {
  protected basePath = "/api/workspaces/workspace/projects/project";
}

const responseWithStatus = (status: number) => ({ status }) as AxiosResponse;

describe("PageCoreService.checkLiveEditAccess", () => {
  let service: TestPageService;

  beforeEach(() => {
    service = new TestPageService();
  });

  it("accepts the dedicated endpoint's 204 response", async () => {
    vi.spyOn(service, "get").mockResolvedValue(responseWithStatus(204));

    await expect(service.checkLiveEditAccess("page-id")).resolves.toBeUndefined();
    expect(service.get).toHaveBeenCalledWith(
      "/api/workspaces/workspace/projects/project/pages/page-id/live-edit-access/",
      {
        headers: {},
        timeout: LIVE_AUTHORIZATION_REQUEST_TIMEOUT_MS,
      }
    );
  });

  it("rejects any other successful HTTP response", async () => {
    vi.spyOn(service, "get").mockResolvedValue(responseWithStatus(200));

    await expect(service.checkLiveEditAccess("page-id")).rejects.toThrow("Unexpected Live authorization response");
  });
});

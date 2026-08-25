/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Connection, Hocuspocus, onConfigurePayload } from "@hocuspocus/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  revalidateLiveEditAuthorization: vi.fn(),
}));

vi.mock("@plane/logger", () => ({
  logger: {
    error: vi.fn(),
  },
}));

vi.mock("@/lib/auth", () => ({
  LIVE_AUTHORIZATION_TTL_MS: 10_000,
  revalidateLiveEditAuthorization: mocks.revalidateLiveEditAuthorization,
}));

import { LiveAuthorizationSweeper } from "@/extensions/live-authorization-sweeper";
import { CloseCode, ForceCloseReason } from "@/types/server-commands";

const context = {
  cookie: "session-cookie",
  documentType: "project_page",
  projectId: "22222222-2222-4222-8222-222222222222",
  userId: "11111111-1111-4111-8111-111111111111",
  workspaceSlug: "workspace-slug",
};

const connection = () =>
  ({
    context: { ...context },
    close: vi.fn(),
  }) as unknown as Connection;

const instanceWith = (...connections: Connection[]) =>
  ({
    documents: new Map([
      [
        "33333333-3333-4333-8333-333333333333",
        {
          name: "33333333-3333-4333-8333-333333333333",
          connections: new Map(connections.map((current, index) => [`socket-${index}`, { connection: current }])),
        },
      ],
    ]),
  }) as unknown as Hocuspocus;

const configurePayload = (instance: Hocuspocus) =>
  ({
    instance,
    configuration: { extensions: [] },
    version: "test",
  }) as unknown as onConfigurePayload;

describe("LiveAuthorizationSweeper", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    mocks.revalidateLiveEditAuthorization.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("revalidates a completely passive connection every authorization interval", async () => {
    const passiveConnection = connection();
    const instance = instanceWith(passiveConnection);
    const sweeper = new LiveAuthorizationSweeper();
    await sweeper.onConfigure(configurePayload(instance));

    await vi.advanceTimersByTimeAsync(10_000);

    expect(mocks.revalidateLiveEditAuthorization).toHaveBeenCalledWith({
      context: passiveConnection.context,
      documentName: "33333333-3333-4333-8333-333333333333",
      force: true,
    });
    expect(passiveConnection.close).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(10_000);
    expect(mocks.revalidateLiveEditAuthorization).toHaveBeenCalledTimes(2);

    await sweeper.onDestroy();
  });

  it("closes a passive connection with the security close code when revalidation fails", async () => {
    mocks.revalidateLiveEditAuthorization.mockRejectedValue(new Error("forbidden"));
    const passiveConnection = connection();
    const sweeper = new LiveAuthorizationSweeper();
    await sweeper.onConfigure(configurePayload(instanceWith(passiveConnection)));

    await vi.advanceTimersByTimeAsync(10_000);

    expect(passiveConnection.close).toHaveBeenCalledWith({
      code: CloseCode.SECURITY_VIOLATION,
      reason: ForceCloseReason.SECURITY_VIOLATION,
    });

    await sweeper.onDestroy();
  });

  it("continues the sweep when closing a denied socket throws", async () => {
    mocks.revalidateLiveEditAuthorization.mockRejectedValue(new Error("forbidden"));
    const brokenConnection = connection();
    vi.mocked(brokenConnection.close).mockImplementation(() => {
      throw new Error("socket already broken");
    });
    const healthyConnection = connection();
    const sweeper = new LiveAuthorizationSweeper();

    await expect(sweeper.sweep(instanceWith(brokenConnection, healthyConnection))).resolves.toBeUndefined();

    expect(brokenConnection.close).toHaveBeenCalledWith({
      code: CloseCode.SECURITY_VIOLATION,
      reason: ForceCloseReason.SECURITY_VIOLATION,
    });
    expect(healthyConnection.close).toHaveBeenCalledWith({
      code: CloseCode.SECURITY_VIOLATION,
      reason: ForceCloseReason.SECURITY_VIOLATION,
    });
  });

  it("coalesces overlapping interval checks per connection", async () => {
    let resolveValidation: (() => void) | undefined;
    mocks.revalidateLiveEditAuthorization.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveValidation = resolve;
      })
    );
    const passiveConnection = connection();
    const sweeper = new LiveAuthorizationSweeper();
    await sweeper.onConfigure(configurePayload(instanceWith(passiveConnection)));

    await vi.advanceTimersByTimeAsync(20_000);
    expect(mocks.revalidateLiveEditAuthorization).toHaveBeenCalledOnce();

    resolveValidation?.();
    await Promise.resolve();
    await Promise.resolve();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(mocks.revalidateLiveEditAuthorization).toHaveBeenCalledTimes(2);

    resolveValidation?.();
    await sweeper.onDestroy();
  });

  it("clears its interval when the server is destroyed", async () => {
    const passiveConnection = connection();
    const sweeper = new LiveAuthorizationSweeper();
    await sweeper.onConfigure(configurePayload(instanceWith(passiveConnection)));
    await sweeper.onDestroy();

    await vi.advanceTimersByTimeAsync(30_000);

    expect(mocks.revalidateLiveEditAuthorization).not.toHaveBeenCalled();
  });
});

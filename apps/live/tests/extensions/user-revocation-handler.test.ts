/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Connection, Hocuspocus } from "@hocuspocus/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@plane/logger", () => ({
  logger: {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  },
}));

vi.mock("@/extensions/redis", () => ({
  Redis: Object,
}));

import { closeRevokedUserConnections } from "@/extensions/user-revocation-handler";
import { ServerCommand, CloseCode, ForceCloseReason } from "@/types/server-commands";

const connectionFor = (userId: string) =>
  ({
    context: { userId },
    sendStateless: vi.fn(),
    close: vi.fn(),
  }) as unknown as Connection;

describe("UserRevocationHandler", () => {
  it("closes only the revoked user's connections across documents", () => {
    const revokedConnection = connectionFor("revoked-user");
    const secondRevokedConnection = connectionFor("revoked-user");
    const allowedConnection = connectionFor("allowed-user");
    const instance = {
      documents: new Map([
        [
          "page-one",
          {
            connections: new Map([
              ["socket-one", { connection: revokedConnection }],
              ["socket-two", { connection: allowedConnection }],
            ]),
          },
        ],
        [
          "page-two",
          {
            connections: new Map([["socket-three", { connection: secondRevokedConnection }]]),
          },
        ],
      ]),
    } as unknown as Hocuspocus;

    const closed = closeRevokedUserConnections(instance, {
      command: ServerCommand.REVOKE_USER,
      userId: "revoked-user",
      accessChangedAt: "2026-08-24T00:00:00+00:00",
      originServer: "api",
    });

    expect(closed).toBe(2);
    expect(revokedConnection.sendStateless).toHaveBeenCalledOnce();
    expect(revokedConnection.close).toHaveBeenCalledWith({
      code: CloseCode.SECURITY_VIOLATION,
      reason: ForceCloseReason.SECURITY_VIOLATION,
    });
    expect(secondRevokedConnection.close).toHaveBeenCalledOnce();
    expect(allowedConnection.sendStateless).not.toHaveBeenCalled();
    expect(allowedConnection.close).not.toHaveBeenCalled();
  });
});

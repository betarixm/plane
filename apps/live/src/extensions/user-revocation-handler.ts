/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Connection, Extension, Hocuspocus, onConfigurePayload } from "@hocuspocus/server";
import { logger } from "@plane/logger";
import { Redis } from "@/extensions/redis";
import {
  ServerCommand,
  CloseCode,
  ForceCloseReason,
  getForceCloseMessage,
  isRevokeUserCommand,
} from "@/types/server-commands";
import type { ClientForceCloseMessage, RevokeUserCommandData } from "@/types/server-commands";
import type { HocusPocusServerContext } from "@/types";

export const closeRevokedUserConnections = (instance: Hocuspocus, data: RevokeUserCommandData): number => {
  const connections = new Set<Connection>();

  instance.documents.forEach((document) => {
    document.connections.forEach(({ connection }) => {
      const context = connection.context as Partial<HocusPocusServerContext>;
      if (context.userId === data.userId) {
        connections.add(connection);
      }
    });
  });

  const forceCloseMessage: ClientForceCloseMessage = {
    type: "force_close",
    reason: ForceCloseReason.SECURITY_VIOLATION,
    code: CloseCode.SECURITY_VIOLATION,
    message: getForceCloseMessage(ForceCloseReason.SECURITY_VIOLATION),
    timestamp: new Date().toISOString(),
  };

  connections.forEach((connection) => {
    try {
      connection.sendStateless(JSON.stringify(forceCloseMessage));
    } catch (error) {
      logger.error("[USER_REVOCATION_HANDLER] Failed to notify connection:", error);
    }

    try {
      connection.close({
        code: CloseCode.SECURITY_VIOLATION,
        reason: ForceCloseReason.SECURITY_VIOLATION,
      });
    } catch (error) {
      logger.error("[USER_REVOCATION_HANDLER] Failed to close connection:", error);
    }
  });

  return connections.size;
};

/**
 * Close a user's page connections on every Live server when Slack changes
 * their workspace access. Reconnects must pass backend authorization again.
 */
export class UserRevocationHandler implements Extension {
  name = "UserRevocationHandler";
  priority = 999;

  async onConfigure({ instance }: onConfigurePayload) {
    const redisExt = instance.configuration.extensions.find((extension) => extension instanceof Redis);
    if (!redisExt) {
      logger.warn("[USER_REVOCATION_HANDLER] Redis extension not found");
      return;
    }

    redisExt.onServerCommand<RevokeUserCommandData>(ServerCommand.REVOKE_USER, (data) => {
      if (!isRevokeUserCommand(data)) {
        logger.error("[USER_REVOCATION_HANDLER] Received invalid revoke user command");
        return;
      }

      const closed = closeRevokedUserConnections(instance, data);
      logger.info(`[USER_REVOCATION_HANDLER] Closed ${closed} connection(s) for user ${data.userId}`);
    });

    logger.info("[USER_REVOCATION_HANDLER] Registered with Redis extension");
  }
}

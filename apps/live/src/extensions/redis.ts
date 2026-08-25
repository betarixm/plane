/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Redis as HocuspocusRedis } from "@hocuspocus/extension-redis";
import { OutgoingMessage } from "@hocuspocus/server";
import type { onConfigurePayload } from "@hocuspocus/server";
import { logger } from "@plane/logger";
import { AppError } from "@/lib/errors";
import { redisManager } from "@/redis";
import { ServerCommand } from "@/types/server-commands";
import type { ServerCommandData, ServerCommandHandler } from "@/types/server-commands";

const getRedisClient = () => {
  const redisClient = redisManager.getClient();
  if (!redisClient) {
    throw new AppError("Redis client not initialized");
  }
  return redisClient;
};

export class Redis extends HocuspocusRedis {
  private serverHandlers = new Map<ServerCommand, ServerCommandHandler>();
  private readonly SERVER_CHANNEL = "hocuspocus:server";

  constructor() {
    super({ redis: getRedisClient() });
  }

  async onConfigure(payload: onConfigurePayload) {
    await super.onConfigure(payload);

    // Subscribe to server channel
    await new Promise<void>((resolve, reject) => {
      this.sub.subscribe(this.SERVER_CHANNEL, (error: Error) => {
        if (error) {
          logger.error(`[Redis] Failed to subscribe to server channel:`, error);
          reject(error);
        } else {
          logger.info(`[Redis] Subscribed to server channel: ${this.SERVER_CHANNEL}`);
          resolve();
        }
      });
    });

    // Listen for server messages
    this.sub.on("message", this.handleServerMessage);
    logger.info(`[Redis] Attached server message listener`);
  }

  private handleServerMessage = async (channel: string, message: string) => {
    if (channel !== this.SERVER_CHANNEL) return;

    try {
      const data = JSON.parse(message) as ServerCommandData;

      // Validate command
      if (!data.command || !Object.values(ServerCommand).includes(data.command as ServerCommand)) {
        logger.warn(`[Redis] Invalid server command received: ${data.command}`);
        return;
      }

      const handler = this.serverHandlers.get(data.command);

      if (handler) {
        await handler(data);
      } else {
        logger.warn(`[Redis] No handler registered for server command: ${data.command}`);
      }
    } catch (error) {
      logger.error("[Redis] Error handling server message:", error);
    }
  };

  /**
   * Register a handler for a server command.
   */
  public onServerCommand<T extends ServerCommandData = ServerCommandData>(
    command: ServerCommand,
    handler: ServerCommandHandler<T>
  ) {
    this.serverHandlers.set(command, handler as ServerCommandHandler);
    logger.info(`[Redis] Registered server command: ${command}`);
  }

  /**
   * Publish server command to global channel
   */
  public async publishServerCommand<T extends ServerCommandData>(data: T): Promise<number> {
    // Validate command data
    if (!data.command || !Object.values(ServerCommand).includes(data.command)) {
      throw new AppError(`Invalid server command: ${data.command}`);
    }

    const message = JSON.stringify(data);
    const receivers = await this.pub.publish(this.SERVER_CHANNEL, message);

    logger.info(`[Redis] Published "${data.command}" command, received by ${receivers} server(s)`);
    return receivers;
  }

  async onDestroy() {
    // Unsubscribe from server channel
    await new Promise<void>((resolve) => {
      this.sub.unsubscribe(this.SERVER_CHANNEL, (error: Error) => {
        if (error) {
          logger.error(`[Redis] Error unsubscribing from server channel:`, error);
        }
        resolve();
      });
    });

    // Remove the message listener to prevent memory leaks
    this.sub.removeListener("message", this.handleServerMessage);
    logger.info(`[Redis] Removed server message listener`);

    await super.onDestroy();
  }

  /**
   * Broadcast a message to a document across all servers via Redis.
   * Uses empty identifier so ALL servers process the message.
   */
  public async broadcastToDocument(documentName: string, payload: unknown): Promise<number> {
    const stringPayload = typeof payload === "string" ? payload : JSON.stringify(payload);

    const message = new OutgoingMessage(documentName).writeBroadcastStateless(stringPayload);

    const emptyPrefix = Buffer.concat([Buffer.from([0])]);
    const channel = this["pubKey"](documentName);
    const encodedMessage = Buffer.concat([emptyPrefix, Buffer.from(message.toUint8Array())]);

    const result = await this.pub.publishBuffer(channel, encodedMessage);

    logger.info(`REDIS_EXTENSION: Published to ${documentName}, ${result} subscribers`);

    return result;
  }
}

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Connection, Extension, Hocuspocus, onConfigurePayload } from "@hocuspocus/server";
import { logger } from "@plane/logger";
import { revalidateLiveEditAuthorization } from "@/lib/auth";
import { LIVE_AUTHORIZATION_TTL_MS } from "@/lib/live-authorization-constants";
import type { HocusPocusServerContext } from "@/types";
import { CloseCode, ForceCloseReason } from "@/types/server-commands";

type LiveConnection = {
  connection: Connection;
  documentName: string;
};

const liveConnections = (instance: Hocuspocus): LiveConnection[] => {
  const connections = new Set<Connection>();
  const result: LiveConnection[] = [];

  instance.documents.forEach((document) => {
    document.connections.forEach(({ connection }) => {
      if (connections.has(connection)) return;
      connections.add(connection);
      result.push({ connection, documentName: document.name });
    });
  });

  return result;
};

/**
 * Revalidate every open editor even when its client is completely passive.
 *
 * The inbound message hook remains the fast write gate. This sweep is the
 * read-side revocation gate: a socket that only receives Yjs broadcasts must
 * still prove its session and page access once per authorization interval.
 */
export class LiveAuthorizationSweeper implements Extension {
  name = "LiveAuthorizationSweeper";
  priority = 998;

  private interval: ReturnType<typeof setInterval> | undefined;
  private validationPromises = new WeakMap<Connection, Promise<void>>();

  async onConfigure({ instance }: onConfigurePayload): Promise<void> {
    this.stop();
    this.interval = setInterval(() => {
      void this.sweep(instance);
    }, LIVE_AUTHORIZATION_TTL_MS);
    this.interval.unref?.();
  }

  async onDestroy(): Promise<void> {
    this.stop();
  }

  async sweep(instance: Hocuspocus): Promise<void> {
    await Promise.all(
      liveConnections(instance).map(({ connection, documentName }) => this.validate(connection, documentName))
    );
  }

  private validate(connection: Connection, documentName: string): Promise<void> {
    const existingValidation = this.validationPromises.get(connection);
    if (existingValidation) return existingValidation;

    const validation = Promise.resolve()
      .then(() =>
        revalidateLiveEditAuthorization({
          context: connection.context as HocusPocusServerContext,
          documentName,
          force: true,
        })
      )
      .catch((error) => {
        logger.error("[LIVE_AUTHORIZATION_SWEEPER] Passive connection authorization failed", error);
        try {
          connection.close({
            code: CloseCode.SECURITY_VIOLATION,
            reason: ForceCloseReason.SECURITY_VIOLATION,
          });
        } catch (closeError) {
          // A broken socket must not reject the interval callback and prevent
          // the remaining connections from being checked.
          logger.error("[LIVE_AUTHORIZATION_SWEEPER] Failed to close denied connection", closeError);
        }
      })
      .finally(() => {
        if (this.validationPromises.get(connection) === validation) {
          this.validationPromises.delete(connection);
        }
      });

    this.validationPromises.set(connection, validation);
    return validation;
  }

  private stop(): void {
    if (this.interval !== undefined) {
      clearInterval(this.interval);
      this.interval = undefined;
    }
    this.validationPromises = new WeakMap<Connection, Promise<void>>();
  }
}

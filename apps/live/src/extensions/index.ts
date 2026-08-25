/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Database } from "./database";
import { ForceCloseHandler } from "./force-close-handler";
import { LiveAuthorizationSweeper } from "./live-authorization-sweeper";
import { Logger } from "./logger";
import { Redis } from "./redis";
import { TitleSyncExtension } from "./title-sync";
import { UserRevocationHandler } from "./user-revocation-handler";

export const getExtensions = () => [
  new Logger(),
  new Database(),
  new Redis(),
  new TitleSyncExtension(),
  new ForceCloseHandler(), // Must be after Redis to receive broadcasts
  new UserRevocationHandler(), // Must be after Redis to receive broadcasts
  new LiveAuthorizationSweeper(), // Revalidate passive/read-only sockets without relying on inbound messages
];

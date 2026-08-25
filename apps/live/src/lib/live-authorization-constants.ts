/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Passive sockets begin a fresh authorization check at least this often. */
export const LIVE_AUTHORIZATION_TTL_MS = 10_000;

/**
 * Do not inherit the general 20-second API timeout for a security check. A
 * silent backend is treated as denied after five seconds, so the periodic
 * sweep has a finite fail-closed bound as well as a bounded success interval.
 */
export const LIVE_AUTHORIZATION_REQUEST_TIMEOUT_MS = 5_000;

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Type-safe commands for server-to-server communication.
 */

/**
 * Force close error codes - reasons why a document is being force closed
 */
export enum ForceCloseReason {
  CRITICAL_ERROR = "critical_error",
  DOCUMENT_TOO_LARGE = "document_too_large",
  SECURITY_VIOLATION = "security_violation",
}

/**
 * WebSocket close codes
 * https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code
 */
export enum CloseCode {
  /** Custom: Force close requested */
  FORCE_CLOSE = 4000,
  /** Custom: Document too large */
  DOCUMENT_TOO_LARGE = 4001,
  /** Custom: Security violation */
  SECURITY_VIOLATION = 4003,
}

/**
 * Server command types.
 */
export enum ServerCommand {
  FORCE_CLOSE = "force_close",
  REVOKE_USER = "revoke_user",
}

/**
 * Force close command data structure
 */
export interface ForceCloseCommandData {
  command: ServerCommand.FORCE_CLOSE;
  docId: string;
  reason: ForceCloseReason;
  code: CloseCode;
  originServer: string;
  timestamp?: string;
}

/**
 * Revoke all cached Live authorization for one user.
 */
export interface RevokeUserCommandData {
  command: ServerCommand.REVOKE_USER;
  userId: string;
  accessChangedAt: string;
  originServer: string;
  timestamp?: string;
}

/**
 * Union type for all server commands.
 */
export type ServerCommandData = ForceCloseCommandData | RevokeUserCommandData;

/**
 * Client force close message structure (sent to clients via sendStateless)
 */
export interface ClientForceCloseMessage {
  type: "force_close";
  reason: ForceCloseReason;
  code: CloseCode;
  message?: string;
  timestamp?: string;
}

/**
 * Server command handler function type.
 */
export type ServerCommandHandler<T extends ServerCommandData = ServerCommandData> = (data: T) => Promise<void> | void;

/**
 * Type guard to check if data is a ForceCloseCommandData
 */
export function isForceCloseCommand(data: ServerCommandData): data is ForceCloseCommandData {
  return data.command === ServerCommand.FORCE_CLOSE;
}

/**
 * Type guard to check if data is a valid RevokeUserCommandData.
 */
export function isRevokeUserCommand(data: ServerCommandData): data is RevokeUserCommandData {
  return (
    data.command === ServerCommand.REVOKE_USER &&
    typeof data.userId === "string" &&
    data.userId.length > 0 &&
    typeof data.accessChangedAt === "string" &&
    typeof data.originServer === "string"
  );
}

/**
 * Get human-readable message for force close reason
 */
export function getForceCloseMessage(reason: ForceCloseReason): string {
  const messages: Record<ForceCloseReason, string> = {
    [ForceCloseReason.CRITICAL_ERROR]: "A critical error occurred. Please refresh the page.",
    [ForceCloseReason.DOCUMENT_TOO_LARGE]:
      "Content limit reached and live sync is off. Create a new page or use nested pages to continue syncing.",
    [ForceCloseReason.SECURITY_VIOLATION]: "Security violation detected. Connection terminated.",
  };

  return messages[reason] || "Connection closed. Please refresh the page.";
}

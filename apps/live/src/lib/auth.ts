/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { IncomingHttpHeaders } from "http";
import type { beforeHandleMessagePayload } from "@hocuspocus/server";
import type { TUserDetails } from "@plane/editor";
import { logger } from "@plane/logger";
import { AppError } from "@/lib/errors";
import { LIVE_AUTHORIZATION_TTL_MS } from "@/lib/live-authorization-constants";
// services
import { UserService } from "@/services/user.service";
import { getPageService } from "@/services/page/handler";
// types
import type { HocusPocusServerContext, TDocumentTypes } from "@/types";
import { CloseCode, ForceCloseReason } from "@/types/server-commands";

export { LIVE_AUTHORIZATION_TTL_MS } from "@/lib/live-authorization-constants";
const WORKSPACE_SLUG_PATTERN = /^[A-Za-z0-9_-]{1,48}$/;
const CANONICAL_UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

class LiveAuthorizationCloseError extends Error {
  readonly code = CloseCode.SECURITY_VIOLATION;
  readonly reason = ForceCloseReason.SECURITY_VIOLATION;

  constructor() {
    super("Live edit authorization expired");
    this.name = "LiveAuthorizationCloseError";
  }
}

const assertValidLiveAuthorizationContext = (context: HocusPocusServerContext, documentName: string): void => {
  if (
    context.documentType !== "project_page" ||
    !context.workspaceSlug ||
    !WORKSPACE_SLUG_PATTERN.test(context.workspaceSlug) ||
    !context.projectId ||
    !CANONICAL_UUID_PATTERN.test(context.projectId) ||
    !CANONICAL_UUID_PATTERN.test(documentName) ||
    !CANONICAL_UUID_PATTERN.test(context.userId)
  ) {
    throw new AppError("Invalid Live authorization context", { code: "AUTH_INVALID_LIVE_CONTEXT" });
  }
};

/**
 * Authenticate the user
 * @param requestHeaders - The request headers
 * @param context - The context
 * @param token - The token
 * @returns The authenticated user
 */
export const onAuthenticate = async ({
  requestHeaders,
  requestParameters,
  context,
  documentName,
  token,
}: {
  requestHeaders: IncomingHttpHeaders;
  context: HocusPocusServerContext;
  requestParameters: URLSearchParams;
  documentName: string;
  token: string;
}) => {
  let cookie: string | undefined = undefined;
  let userId: string | undefined = undefined;

  // Extract cookie (fallback to request headers) and userId from token (for scenarios where
  // the cookies are not passed in the request headers)
  try {
    const parsedToken = JSON.parse(token) as TUserDetails;
    userId = parsedToken.id;
    cookie = parsedToken.cookie;
  } catch (error) {
    const appError = new AppError(error, {
      context: { operation: "onAuthenticate" },
    });
    logger.error("Token parsing failed, using request headers", appError);
  } finally {
    // If cookie is still not found, fallback to request headers
    if (!cookie) {
      cookie = requestHeaders.cookie?.toString();
    }
  }

  if (!cookie || !userId) {
    const appError = new AppError("Credentials not provided", { code: "AUTH_MISSING_CREDENTIALS" });
    logger.error("Credentials not provided", appError);
    throw appError;
  }

  // set cookie in context, so it can be used throughout the ws connection
  context.cookie = cookie ?? requestParameters.get("cookie") ?? "";
  context.documentType = requestParameters.get("documentType")?.toString() as TDocumentTypes;
  context.projectId = requestParameters.get("projectId");
  context.userId = userId;
  context.workspaceSlug = requestParameters.get("workspaceSlug");

  assertValidLiveAuthorizationContext(context, documentName);

  const authentication = await handleAuthentication({
    cookie: context.cookie,
    userId: context.userId,
  });

  await handleLiveEditAuthorization({ context, documentName });
  const authenticatedAt = Date.now();

  return {
    ...authentication,
    authenticatedAt,
    authorizationValidatedAt: authenticatedAt,
  };
};

export const handleAuthentication = async ({ cookie, userId }: { cookie: string; userId: string }) => {
  // fetch current user info
  try {
    const userService = new UserService();
    const user = await userService.currentUser(cookie);
    if (user.id !== userId) {
      throw new AppError("Authentication unsuccessful: User ID mismatch", { code: "AUTH_USER_MISMATCH" });
    }

    return {
      user: {
        id: user.id,
        name: user.display_name,
      },
    };
  } catch (error) {
    const appError = new AppError(error, {
      context: { operation: "handleAuthentication" },
    });
    logger.error("Authentication failed", appError);
    throw new AppError("Authentication unsuccessful", { code: appError.code });
  }
};

export const handleLiveEditAuthorization = async ({
  context,
  documentName,
}: {
  context: HocusPocusServerContext;
  documentName: string;
}): Promise<void> => {
  try {
    assertValidLiveAuthorizationContext(context, documentName);
    const pageService = getPageService(context.documentType, context);
    await pageService.checkLiveEditAccess(documentName);
  } catch (error) {
    const appError = new AppError(error, {
      context: { operation: "handleLiveEditAuthorization", documentName },
    });
    logger.error("Live edit authorization failed", appError);
    throw new AppError("Live edit authorization unsuccessful", { code: appError.code });
  }
};

export const revalidateLiveEditAuthorization = async ({
  context,
  documentName,
  force = false,
}: {
  context: HocusPocusServerContext;
  documentName: string;
  force?: boolean;
}): Promise<void> => {
  assertValidLiveAuthorizationContext(context, documentName);

  const validatedAt = context.authorizationValidatedAt;
  if (!force && validatedAt !== undefined && Date.now() - validatedAt < LIVE_AUTHORIZATION_TTL_MS) {
    return;
  }

  const validationPromise =
    context.authorizationValidationPromise ??
    (async () => {
      await handleLiveEditAuthorization({ context, documentName });
      context.authorizationValidatedAt = Date.now();
    })().finally(() => {
      context.authorizationValidationPromise = undefined;
    });

  context.authorizationValidationPromise = validationPromise;
  await validationPromise;
};

export const beforeHandleMessage = async ({
  context,
  documentName,
}: Pick<beforeHandleMessagePayload, "context" | "documentName">): Promise<void> => {
  try {
    const liveContext = context as HocusPocusServerContext;
    await revalidateLiveEditAuthorization({ context: liveContext, documentName });
  } catch {
    // Hocuspocus v2 forwards any present `error.code` directly to ws.close().
    // Never leak Axios/AppError string codes into that numeric close-code slot.
    throw new LiveAuthorizationCloseError();
  }
};

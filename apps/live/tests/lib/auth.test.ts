/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  checkLiveEditAccess: vi.fn(),
  currentUser: vi.fn(),
}));

vi.mock("@plane/logger", () => ({
  logger: {
    error: vi.fn(),
  },
}));

vi.mock("@/services/user.service", () => ({
  UserService: class {
    currentUser = mocks.currentUser;
  },
}));

vi.mock("@/services/page/handler", () => ({
  getPageService: vi.fn(() => ({
    checkLiveEditAccess: mocks.checkLiveEditAccess,
  })),
}));

import { beforeHandleMessage, LIVE_AUTHORIZATION_TTL_MS, onAuthenticate } from "@/lib/auth";
import type { HocusPocusServerContext } from "@/types";
import { CloseCode, ForceCloseReason } from "@/types/server-commands";

const USER_ID = "11111111-1111-4111-8111-111111111111";
const PROJECT_ID = "22222222-2222-4222-8222-222222222222";
const PAGE_ID = "33333333-3333-4333-8333-333333333333";

const createContext = (): HocusPocusServerContext => ({
  projectId: null,
  cookie: "",
  documentType: "project_page",
  workspaceSlug: null,
  userId: "",
});

describe("Live authorization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.currentUser.mockResolvedValue({
      id: USER_ID,
      display_name: "Slack User",
    });
    mocks.checkLiveEditAccess.mockResolvedValue(undefined);
  });

  it("checks current Slack identity and page edit access during authentication", async () => {
    const context = createContext();

    const result = await onAuthenticate({
      requestHeaders: {},
      requestParameters: new URLSearchParams({
        documentType: "project_page",
        projectId: PROJECT_ID,
        workspaceSlug: "workspace-slug",
      }),
      context,
      documentName: PAGE_ID,
      token: JSON.stringify({ id: USER_ID, cookie: "session-cookie" }),
    });

    expect(mocks.currentUser).toHaveBeenCalledWith("session-cookie");
    expect(mocks.checkLiveEditAccess).toHaveBeenCalledWith(PAGE_ID);
    expect(result.user).toEqual({ id: USER_ID, name: "Slack User" });
    expect(result.authenticatedAt).toEqual(expect.any(Number));
    expect(result.authorizationValidatedAt).toBe(result.authenticatedAt);
  });

  it("fails authentication when the user cannot edit the page", async () => {
    mocks.checkLiveEditAccess.mockRejectedValue(new Error("forbidden"));

    await expect(
      onAuthenticate({
        requestHeaders: {},
        requestParameters: new URLSearchParams({
          documentType: "project_page",
          projectId: PROJECT_ID,
          workspaceSlug: "workspace-slug",
        }),
        context: createContext(),
        documentName: PAGE_ID,
        token: JSON.stringify({ id: USER_ID, cookie: "session-cookie" }),
      })
    ).rejects.toThrow("Live edit authorization unsuccessful");
  });

  it.each([
    {
      name: "workspace traversal",
      workspaceSlug: "../users/me?x=",
      projectId: PROJECT_ID,
      documentName: PAGE_ID,
      userId: USER_ID,
    },
    {
      name: "malformed project id",
      workspaceSlug: "workspace-slug",
      projectId: "../users/me",
      documentName: PAGE_ID,
      userId: USER_ID,
    },
    {
      name: "malformed page id",
      workspaceSlug: "workspace-slug",
      projectId: PROJECT_ID,
      documentName: "../../users/me",
      userId: USER_ID,
    },
    {
      name: "malformed user id",
      workspaceSlug: "workspace-slug",
      projectId: PROJECT_ID,
      documentName: PAGE_ID,
      userId: "not-a-uuid",
    },
  ])("rejects $name before calling an API service", async ({ workspaceSlug, projectId, documentName, userId }) => {
    await expect(
      onAuthenticate({
        requestHeaders: {},
        requestParameters: new URLSearchParams({
          documentType: "project_page",
          projectId,
          workspaceSlug,
        }),
        context: createContext(),
        documentName,
        token: JSON.stringify({ id: userId, cookie: "session-cookie" }),
      })
    ).rejects.toThrow("Invalid Live authorization context");

    expect(mocks.currentUser).not.toHaveBeenCalled();
    expect(mocks.checkLiveEditAccess).not.toHaveBeenCalled();
  });

  it("revalidates stale authorization before accepting another message", async () => {
    const context = {
      ...createContext(),
      cookie: "session-cookie",
      projectId: PROJECT_ID,
      workspaceSlug: "workspace-slug",
      userId: USER_ID,
      authorizationValidatedAt: Date.now() - LIVE_AUTHORIZATION_TTL_MS - 1,
    };

    await beforeHandleMessage({ context, documentName: PAGE_ID });

    expect(mocks.checkLiveEditAccess).toHaveBeenCalledOnce();
    expect(context.authorizationValidatedAt).toBeGreaterThan(Date.now() - LIVE_AUTHORIZATION_TTL_MS);
  });

  it("coalesces concurrent stale authorization checks", async () => {
    let resolveCheck: (() => void) | undefined;
    mocks.checkLiveEditAccess.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveCheck = resolve;
      })
    );
    const context = {
      ...createContext(),
      cookie: "session-cookie",
      projectId: PROJECT_ID,
      workspaceSlug: "workspace-slug",
      userId: USER_ID,
      authorizationValidatedAt: 0,
    };

    const first = beforeHandleMessage({ context, documentName: PAGE_ID });
    const second = beforeHandleMessage({ context, documentName: PAGE_ID });

    expect(mocks.checkLiveEditAccess).toHaveBeenCalledOnce();
    resolveCheck?.();
    await Promise.all([first, second]);
    expect(context.authorizationValidationPromise).toBeUndefined();
  });

  it("uses the cached authorization only inside the TTL", async () => {
    const context = {
      ...createContext(),
      projectId: PROJECT_ID,
      workspaceSlug: "workspace-slug",
      userId: USER_ID,
      authorizationValidatedAt: Date.now(),
    };

    await beforeHandleMessage({ context, documentName: PAGE_ID });

    expect(mocks.checkLiveEditAccess).not.toHaveBeenCalled();
  });

  it("exposes a numeric WebSocket close code when TTL authorization is denied", async () => {
    mocks.checkLiveEditAccess.mockRejectedValue(new Error("forbidden"));
    const context = {
      ...createContext(),
      cookie: "session-cookie",
      projectId: PROJECT_ID,
      workspaceSlug: "workspace-slug",
      userId: USER_ID,
      authorizationValidatedAt: 0,
    };

    const error = await beforeHandleMessage({ context, documentName: PAGE_ID }).catch((caught) => caught);

    expect(error).toMatchObject({
      code: CloseCode.SECURITY_VIOLATION,
      reason: ForceCloseReason.SECURITY_VIOLATION,
    });
    expect(typeof error.code).toBe("number");
  });
});

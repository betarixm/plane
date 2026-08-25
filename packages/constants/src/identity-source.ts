/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIdentitySourceProvider } from "@plane/types";

export type TIdentitySourceDescriptor = {
  label: string;
  organizationLabel: string;
  serverConfigurationHint: string;
};

export const IDENTITY_SOURCE_REGISTRY = {
  slack: {
    label: "Slack",
    organizationLabel: "workspace",
    serverConfigurationHint:
      "Set SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, and SLACK_SIGNING_SECRET on the server, then restart Plane.",
  },
  discord: {
    label: "Discord",
    organizationLabel: "server",
    serverConfigurationHint: "A Discord identity adapter is not installed in this build.",
  },
} as const satisfies Record<TIdentitySourceProvider, TIdentitySourceDescriptor>;

export const getIdentitySourceDescriptor = (provider: TIdentitySourceProvider): TIdentitySourceDescriptor =>
  IDENTITY_SOURCE_REGISTRY[provider];

export type TIdentitySourceSignInErrorCode =
  | "IDENTITY_SOURCE_NOT_CONFIGURED"
  | "IDENTITY_SOURCE_OAUTH_STATE_INVALID"
  | "IDENTITY_SOURCE_OAUTH_ERROR"
  | "IDENTITY_SOURCE_ADMIN_REQUIRED"
  | "IDENTITY_SOURCE_ORGANIZATION_MISMATCH"
  | "EXTERNAL_IDENTITY_NOT_FOUND"
  | "EXTERNAL_IDENTITY_INACTIVE"
  | "IDENTITY_SOURCE_SETUP_NOT_ALLOWED"
  | "EXTERNAL_IDENTITY_INVALID";

const IDENTITY_SOURCE_SIGN_IN_ERRORS = {
  IDENTITY_SOURCE_NOT_CONFIGURED: ({ label }) =>
    `${label} application credentials are not configured on the Plane server.`,
  IDENTITY_SOURCE_OAUTH_STATE_INVALID: ({ label }) => `${label} sign-in expired. Please try again.`,
  IDENTITY_SOURCE_OAUTH_ERROR: ({ label }) => `${label} could not complete sign-in. Please try again.`,
  IDENTITY_SOURCE_ADMIN_REQUIRED: ({ label, organizationLabel }) =>
    `Ask a ${label} ${organizationLabel} administrator to connect this Plane instance.`,
  IDENTITY_SOURCE_ORGANIZATION_MISMATCH: ({ label, organizationLabel }) =>
    `Use an account from the ${label} ${organizationLabel} connected to this Plane instance.`,
  EXTERNAL_IDENTITY_INACTIVE: ({ label, organizationLabel }) =>
    `Your ${label} account is not an active ${organizationLabel} member.`,
  EXTERNAL_IDENTITY_NOT_FOUND: ({ label, organizationLabel }) =>
    `Your ${label} account is not an active member of the connected ${organizationLabel}.`,
  EXTERNAL_IDENTITY_INVALID: ({ label }) => `${label} could not verify your account. Please try again.`,
  IDENTITY_SOURCE_SETUP_NOT_ALLOWED: ({ label, organizationLabel }) =>
    `The ${label} ${organizationLabel} is already connected. Continue with ${label} to sign in.`,
} satisfies Record<TIdentitySourceSignInErrorCode, (descriptor: TIdentitySourceDescriptor) => string>;

export const getIdentitySourceSignInError = (
  provider: TIdentitySourceProvider,
  errorCode: string | null
): string | undefined => {
  if (!errorCode) return undefined;

  const descriptor = getIdentitySourceDescriptor(provider);
  const errorMessage = IDENTITY_SOURCE_SIGN_IN_ERRORS[errorCode as TIdentitySourceSignInErrorCode];
  return errorMessage?.(descriptor) ?? `${descriptor.label} sign-in failed. Please try again.`;
};

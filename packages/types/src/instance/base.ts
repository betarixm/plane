/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export interface IInstanceInfo {
  instance: IInstance;
  config: IInstanceConfig;
}

export interface IInstance {
  is_setup_done: boolean;
}

export type TIdentitySourceProvider = "slack" | "discord";

export interface IIdentitySourceOrganization {
  name: string;
  domain: string | null;
  icon_url: string | null;
}

interface IIdentitySourceConfigBase {
  configured: boolean;
  connected: boolean;
  organization: IIdentitySourceOrganization | null;
  last_synced_at: string | null;
  sync_error?: string | null;
  auth_url: string;
  install_url: string;
}

export interface ISlackIdentitySourceConfig extends IIdentitySourceConfigBase {
  provider: "slack";
}

/** Reserved contract for a future Discord identity adapter. */
export interface IDiscordIdentitySourceConfig extends IIdentitySourceConfigBase {
  provider: "discord";
}

export type IIdentitySourceConfig = ISlackIdentitySourceConfig | IDiscordIdentitySourceConfig;

export interface IInstanceConfig {
  identity_source: IIdentitySourceConfig;
  github_app_name: string | undefined;
  has_unsplash_configured: boolean;
  has_llm_configured: boolean;
  file_size_limit: number | undefined;
  is_self_managed: boolean;
  instance_changelog_url?: string;
}

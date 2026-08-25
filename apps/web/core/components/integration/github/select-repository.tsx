/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import useSWRInfinite from "swr/infinite";
import type { IWorkspaceIntegration } from "@plane/types";
// services
// ui
import { CustomSearchSelect } from "@plane/ui";
// helpers
import { truncateText } from "@plane/utils";
import { ProjectService } from "@/services/project";
// types

type Props = {
  integration: IWorkspaceIntegration;
  value: any;
  label: string | React.ReactNode;
  onChange: (repo: any) => void;
  characterLimit?: number;
};

const projectService = new ProjectService();

export function SelectRepository(props: Props) {
  const { integration, value, label, onChange, characterLimit = 25 } = props;
  const getKey = (pageIndex: number) => {
    if (!integration) return;

    return { integrationId: integration.id, page: pageIndex + 1 };
  };

  const fetchGithubRepos = async ({ integrationId, page }: { integrationId: string; page: number }) => {
    const data = await projectService.getGithubRepositories(integrationId, page);

    return data;
  };

  const { data: paginatedData, size, setSize, isValidating } = useSWRInfinite(getKey, fetchGithubRepos);

  let userRepositories = (paginatedData ?? []).map((data) => data.repositories).flat();
  userRepositories = userRepositories.filter((data) => data?.id);

  const totalCount = paginatedData && paginatedData.length > 0 ? paginatedData[0].total_count : 0;

  const options =
    userRepositories.map((repo) => ({
      value: repo.id,
      query: repo.full_name,
      content: <p>{truncateText(repo.full_name, characterLimit)}</p>,
    })) ?? [];

  if (userRepositories.length < 1) return null;

  return (
    <CustomSearchSelect
      value={value}
      options={options}
      onChange={(val: string) => {
        const repo = userRepositories.find((repo) => repo.id === val);

        onChange(repo);
      }}
      label={label}
      footerOption={
        <>
          {userRepositories && options.length < totalCount && (
            <button
              type="button"
              className="w-full p-1 text-center text-10 text-secondary hover:bg-layer-1"
              onClick={() => setSize(size + 1)}
              disabled={isValidating}
            >
              {isValidating ? "Loading..." : "Click to load more..."}
            </button>
          )}
        </>
      }
      optionsClassName="w-48"
    />
  );
}

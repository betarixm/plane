/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import useSWR, { mutate } from "swr";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IWorkspaceIntegration } from "@plane/types";
// assets
import GithubLogo from "@/app/assets/logos/github-square.png?url";
// components
import { SelectRepository } from "@/components/integration/github/select-repository";
// constants
import { PROJECT_GITHUB_REPOSITORY } from "@plane/constants";
// services
import { ProjectService } from "@/services/project";

type Props = {
  integration: IWorkspaceIntegration;
};

const integrationDetails: { [key: string]: any } = {
  github: {
    logo: GithubLogo,
    description: "Select GitHub repository to enable sync.",
  },
};

// services
const projectService = new ProjectService();

export function IntegrationCard({ integration }: Props) {
  const { workspaceSlug, projectId } = useParams();

  const { data: syncedGithubRepository } = useSWR(projectId ? PROJECT_GITHUB_REPOSITORY(projectId) : null, () =>
    workspaceSlug && projectId && integration
      ? projectService.getProjectGithubRepository(projectId, integration.id)
      : null
  );

  const handleChange = (repo: any) => {
    if (!workspaceSlug || !projectId || !integration) return;

    const {
      html_url,
      owner: { login },
      id,
      name,
    } = repo;

    projectService
      .syncGithubRepository(projectId, integration.id, {
        name,
        owner: login,
        repository_id: id,
        url: html_url,
      })
      .then(() => {
        void mutate(PROJECT_GITHUB_REPOSITORY(projectId));

        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Success!",
          message: `${login}/${name} repository synced with the project successfully.`,
        });
        return undefined;
      })
      .catch((err) => {
        console.error(err);
        setToast({
          type: TOAST_TYPE.ERROR,
          title: "Error!",
          message: "Repository could not be synced with the project. Please try again.",
        });
      });
  };

  if (integration.integration_detail.provider !== "github") return null;

  return (
    <>
      {integration && (
        <div className="flex items-center justify-between gap-2 border-b border-subtle bg-surface-1 px-4 py-6">
          <div className="flex items-start gap-4">
            <div className="h-10 w-10 flex-shrink-0">
              <img
                src={integrationDetails[integration.integration_detail.provider].logo}
                className="h-full w-full object-cover"
                alt={`${integration.integration_detail.title} Logo`}
              />
            </div>
            <div>
              <h3 className="flex items-center gap-4 text-13 font-medium">{integration.integration_detail.title}</h3>
              <p className="text-13 tracking-tight text-secondary">
                {integrationDetails[integration.integration_detail.provider].description}
              </p>
            </div>
          </div>
          {integration.integration_detail.provider === "github" && (
            <SelectRepository
              integration={integration}
              value={
                syncedGithubRepository && syncedGithubRepository.length > 0
                  ? `${syncedGithubRepository[0].repo_detail.owner}/${syncedGithubRepository[0].repo_detail.name}`
                  : null
              }
              label={
                syncedGithubRepository && syncedGithubRepository.length > 0
                  ? `${syncedGithubRepository[0].repo_detail.owner}/${syncedGithubRepository[0].repo_detail.name}`
                  : "Select Repository"
              }
              onChange={handleChange}
            />
          )}
        </div>
      )}
    </>
  );
}

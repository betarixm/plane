/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTheme } from "next-themes";
import { redirect } from "react-router";
import { useTranslation } from "@plane/i18n";
// assets
import emptyIssueDark from "@/app/assets/empty-state/search/issues-dark.webp?url";
import emptyIssueLight from "@/app/assets/empty-state/search/issues-light.webp?url";
// components
import { EmptyState } from "@/components/common/empty-state";
import { LogoSpinner } from "@/components/common/logo-spinner";
// hooks
import { useAppRouter } from "@/hooks/use-app-router";
// services
import { IssueService } from "@/services/issue/issue.service";
import { WorkspaceService } from "@/services/workspace.service";
// types
import type { Route } from "./+types/page";

const issueService = new IssueService();
const workspaceService = new WorkspaceService();

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const { projectId, issueId } = params;

  try {
    const workspace = await workspaceService.userWorkspace();
    if (!workspace) return { error: true };

    const data = await issueService.getIssueMetaFromURL(projectId, issueId);

    if (data) {
      throw redirect(`/browse/${data.project_identifier}-${data.sequence_id}`);
    }

    return { error: true };
  } catch (error) {
    // If it's a redirect, rethrow it
    if (error instanceof Response) {
      throw error;
    }
    // Otherwise return error state
    return { error: true };
  }
}

export default function IssueDetailsPage({ loaderData }: Route.ComponentProps) {
  const router = useAppRouter();
  const { t } = useTranslation();
  const { resolvedTheme } = useTheme();

  if (loaderData.error) {
    return (
      <div className="flex size-full items-center justify-center">
        <EmptyState
          image={resolvedTheme === "dark" ? emptyIssueDark : emptyIssueLight}
          title={t("issue.empty_state.issue_detail.title")}
          description={t("issue.empty_state.issue_detail.description")}
          primaryButton={{
            text: t("issue.empty_state.issue_detail.primary_button.text"),
            onClick: () => router.push("/workspace-views/all-issues/"),
          }}
        />
      </div>
    );
  }

  return (
    <div className="flex size-full items-center justify-center">
      <LogoSpinner />
    </div>
  );
}

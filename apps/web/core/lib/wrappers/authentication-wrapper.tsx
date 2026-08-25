/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useSearchParams, usePathname } from "next/navigation";
import useSWR from "swr";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUser } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";

type TAuthenticationWrapper = {
  children: ReactNode;
  mode?: "guest" | "authenticated";
};

const isSafeAppPath = (path: string): boolean => /^\/(?![\\/])/.test(path) && !path.includes("\\");

export const AuthenticationWrapper = observer(function AuthenticationWrapper(props: TAuthenticationWrapper) {
  const pathname = usePathname();
  const router = useAppRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next_path");
  // props
  const { children, mode = "authenticated" } = props;
  // hooks
  const { isLoading: isUserLoading, data: currentUser, fetchCurrentUser } = useUser();
  const { loader: workspaceLoader, workspace } = useWorkspace();

  const { isLoading: isUserSWRLoading } = useSWR("USER_INFORMATION", async () => await fetchCurrentUser(), {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  const getWorkspaceRedirectionUrl = (): string => {
    // validating the nextPath from the router query
    if (nextPath && isSafeAppPath(nextPath.toString())) {
      return nextPath.toString();
    }

    if (!workspace) return "/";

    return "/home";
  };

  if ((isUserSWRLoading || isUserLoading || workspaceLoader) && !currentUser?.id)
    return (
      <div className="relative flex h-screen w-full items-center justify-center">
        <LogoSpinner />
      </div>
    );

  if (mode === "guest") {
    if (!currentUser?.id) return <>{children}</>;
    else {
      const currentRedirectRoute = getWorkspaceRedirectionUrl();
      router.push(currentRedirectRoute);
      return <></>;
    }
  }

  if (currentUser?.id) return <>{children}</>;

  const requestedPath = `${pathname || "/"}${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  router.push(`/?${new URLSearchParams({ next_path: requestedPath }).toString()}`);
  return <></>;
});

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Fragment, useEffect, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
// icons
import { LogOut, Mails } from "lucide-react";
// ui
import { Menu, Transition } from "@headlessui/react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { ChevronDownIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { cn } from "@plane/utils";
// helpers
import { AppSidebarItem } from "@/components/sidebar/sidebar-item";
// hooks
import { useAppTheme } from "@/hooks/store/use-app-theme";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUser } from "@/hooks/store/user";
// components
import { WorkspaceLogo } from "../logo";

type WorkspaceMenuRootProps = {
  variant: "sidebar" | "top-navigation";
};

export const WorkspaceMenuRoot = observer(function WorkspaceMenuRoot({ variant }: WorkspaceMenuRootProps) {
  const { toggleSidebar, toggleAnySidebarDropdown } = useAppTheme();
  const { data: currentUser, signOut } = useUser();
  const { currentWorkspace } = useWorkspace();
  const { t } = useTranslation();
  const [isWorkspaceMenuOpen, setIsWorkspaceMenuOpen] = useState(false);

  const handleSignOut = async () => {
    await signOut().catch(() =>
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("auth.sign_out.toast.error.title"),
        message: t("auth.sign_out.toast.error.message"),
      })
    );
  };

  const handleItemClick = () => {
    if (window.innerWidth < 768) toggleSidebar();
  };

  useEffect(() => {
    toggleAnySidebarDropdown(isWorkspaceMenuOpen);
  }, [isWorkspaceMenuOpen, toggleAnySidebarDropdown]);

  return (
    <Menu
      as="div"
      className={cn("relative flex h-full w-fit max-w-48 truncate whitespace-nowrap", {
        "w-full justify-center text-center": variant === "sidebar",
        "flex-grow justify-stretch truncate text-left": variant === "top-navigation",
      })}
    >
      {({ open }: { open: boolean }) => {
        if (isWorkspaceMenuOpen !== open) setIsWorkspaceMenuOpen(open);

        return (
          <>
            {variant === "sidebar" && (
              <Menu.Button
                className={cn("flex size-8 w-full items-center justify-center rounded-md", { "bg-layer-1": open })}
              >
                <AppSidebarItem
                  variant="button"
                  item={{
                    icon: (
                      <WorkspaceLogo
                        logo={currentWorkspace?.logo_url}
                        name={currentWorkspace?.name}
                        classNames="size-8 rounded-md border border-subtle"
                      />
                    ),
                  }}
                />
              </Menu.Button>
            )}
            {variant === "top-navigation" && (
              <Menu.Button
                className={cn(
                  "group/menu-button flex flex-grow items-center justify-between gap-1 truncate rounded-sm p-1 text-13 font-medium text-secondary hover:bg-layer-1 focus:outline-none",
                  { "bg-layer-1": open }
                )}
                aria-label="Open workspace menu"
              >
                <div className="flex flex-grow items-center gap-2 truncate">
                  <WorkspaceLogo
                    logo={currentWorkspace?.logo_url}
                    name={currentWorkspace?.name}
                    classNames="size-7 rounded-md border border-subtle"
                  />
                  <h4 className="truncate text-14 font-medium text-primary">
                    {currentWorkspace?.name ?? t("loading")}
                  </h4>
                </div>
                <ChevronDownIcon
                  className={cn("size-4 flex-shrink-0 text-placeholder duration-300", { "rotate-180": open })}
                />
              </Menu.Button>
            )}
            <Transition
              as={Fragment}
              enter="transition ease-out duration-100"
              enterFrom="transform opacity-0 scale-95"
              enterTo="transform opacity-100 scale-100"
              leave="transition ease-in duration-75"
              leaveFrom="transform opacity-100 scale-100"
              leaveTo="transform opacity-0 scale-95"
            >
              <Menu.Items as={Fragment}>
                <div
                  className={cn(
                    "fixed z-21 mt-1 flex w-[19rem] origin-top-left flex-col divide-y divide-subtle rounded-md border-[0.5px] border-strong bg-surface-1 shadow-raised-200 outline-none",
                    {
                      "top-11 left-14": variant === "sidebar",
                      "top-10 left-4": variant === "top-navigation",
                    }
                  )}
                >
                  <div className="flex flex-col px-4 py-3">
                    <span className="truncate pb-2 text-left text-13 font-medium text-placeholder">
                      {currentUser?.email}
                    </span>
                    <div className="flex items-center gap-2.5 rounded-sm bg-layer-transparent-active p-2">
                      <WorkspaceLogo
                        logo={currentWorkspace?.logo_url}
                        name={currentWorkspace?.name}
                        classNames="size-8 shrink-0 rounded-md border border-subtle"
                      />
                      <span className="truncate text-13 font-medium text-primary">
                        {currentWorkspace?.name ?? t("loading")}
                      </span>
                    </div>
                  </div>
                  <div className="flex w-full flex-col items-start justify-start gap-2 px-4 py-2 text-13">
                    <Link href="/invitations" className="w-full" onClick={handleItemClick}>
                      <Menu.Item
                        as="div"
                        className="flex items-center gap-2 rounded-sm px-2 py-1 text-13 font-medium text-secondary hover:bg-layer-transparent-hover"
                      >
                        <Mails className="size-4 shrink-0" />
                        {t("workspace_invites")}
                      </Menu.Item>
                    </Link>
                    <Menu.Item
                      as="button"
                      type="button"
                      className="flex w-full items-center gap-2 rounded-sm px-2 py-1 text-13 font-medium text-danger-primary hover:bg-layer-transparent-hover"
                      onClick={handleSignOut}
                    >
                      <LogOut className="size-4 shrink-0" />
                      {t("sign_out")}
                    </Menu.Item>
                  </div>
                </div>
              </Menu.Items>
            </Transition>
          </>
        );
      }}
    </Menu>
  );
});

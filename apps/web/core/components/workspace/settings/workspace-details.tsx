/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { Controller, useForm } from "react-hook-form";
// Plane Imports
import { EUserPermissions, EUserPermissionsLevel, getIdentitySourceDescriptor } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IWorkspace } from "@plane/types";
import { Input } from "@plane/ui";
import { cn, copyUrlToClipboard, getFileURL } from "@plane/utils";
// components
import { TimezoneSelect } from "@/components/global/timezone-select";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
// plane web components

type TWorkspacePreferencesForm = Pick<IWorkspace, "timezone">;

const defaultValues: TWorkspacePreferencesForm = {
  timezone: "UTC",
};

export const WorkspaceDetails = observer(function WorkspaceDetails() {
  // states
  const [isLoading, setIsLoading] = useState(false);
  // store hooks
  const { currentWorkspace, updateWorkspace } = useWorkspace();
  const { config } = useInstance();
  const { allowPermissions } = useUserPermissions();
  const { t } = useTranslation();
  const identitySource = config?.identity_source;
  const descriptor = identitySource ? getIdentitySourceDescriptor(identitySource.provider) : undefined;

  // form info
  const { handleSubmit, control, reset } = useForm<TWorkspacePreferencesForm>({
    defaultValues: { timezone: currentWorkspace?.timezone ?? defaultValues.timezone },
  });
  const onSubmit = async (formData: TWorkspacePreferencesForm) => {
    if (!currentWorkspace) return;

    setIsLoading(true);

    const payload: Pick<IWorkspace, "timezone"> = {
      timezone: formData.timezone,
    };

    try {
      await updateWorkspace(currentWorkspace.slug, payload);
      setToast({
        title: "Success!",
        type: TOAST_TYPE.SUCCESS,
        message: "Workspace updated successfully",
      });
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setTimeout(() => {
        setIsLoading(false);
      }, 300);
    }
  };

  const handleCopyUrl = () => {
    if (!currentWorkspace) return;

    void copyUrlToClipboard("/home")
      .then(() => {
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Workspace URL copied to the clipboard.",
        });
        return undefined;
      })
      .catch(() => {
        // Silently handle clipboard errors
      });
  };

  useEffect(() => {
    if (currentWorkspace) reset({ timezone: currentWorkspace.timezone });
  }, [currentWorkspace, reset]);

  const isAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE);

  if (!currentWorkspace) return null;

  return (
    <>
      <div className={cn("flex w-full flex-col gap-y-7", { "opacity-60": !isAdmin })}>
        <div className="flex items-center gap-5">
          <div className="flex shrink-0 flex-col gap-1">
            <div>
              {currentWorkspace.logo_url ? (
                <div className="relative flex size-14">
                  <img
                    src={getFileURL(currentWorkspace.logo_url)}
                    className="absolute top-0 left-0 size-full rounded-md object-cover"
                    alt="Workspace Logo"
                  />
                </div>
              ) : (
                <div className="relative grid size-14 place-items-center rounded-md bg-accent-primary text-24 text-on-color uppercase">
                  {currentWorkspace?.name?.charAt(0) ?? "N"}
                </div>
              )}
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <div className="mb:-my-5 text-h5-semibold leading-6">{currentWorkspace.name}</div>
            <button type="button" onClick={handleCopyUrl} className="text-left text-body-xs-regular tracking-tight">{`${
              typeof window !== "undefined" && window.location.origin.replace("http://", "").replace("https://", "")
            }/home`}</button>
            <span className="text-caption-sm-regular text-tertiary">
              Name and logo are managed by {descriptor?.label ?? "your identity source"}
            </span>
          </div>
        </div>
        <div className="flex flex-col gap-7">
          <div className="grid-col grid w-full grid-cols-1 items-center justify-between gap-10 xl:grid-cols-2 2xl:grid-cols-3">
            <div className="flex flex-col gap-2">
              <h4 className="text-body-sm-medium text-tertiary">{t("workspace_settings.settings.general.name")}</h4>
              <Input
                id="name"
                name="name"
                type="text"
                value={currentWorkspace.name}
                className="w-full cursor-not-allowed rounded-md !bg-layer-1"
                disabled
              />
              <p className="text-caption-sm-regular text-tertiary">
                Managed by {descriptor?.label ?? "your identity source"}
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <h4 className="text-body-sm-medium text-tertiary">{t("workspace_settings.settings.general.url")}</h4>
              <Input
                id="url"
                name="url"
                type="url"
                value={`${
                  typeof window !== "undefined" && window.location.origin.replace("http://", "").replace("https://", "")
                }/home`}
                className="w-full cursor-not-allowed rounded-md !bg-layer-1"
                disabled
              />
            </div>
            <div className="flex flex-col gap-2">
              <h4 className="text-body-sm-medium text-tertiary">
                {t("workspace_settings.settings.general.workspace_timezone")}
              </h4>
              <Controller
                name="timezone"
                control={control}
                render={({ field: { value, onChange } }) => (
                  <>
                    <TimezoneSelect value={value} onChange={onChange} disabled={!isAdmin} />
                  </>
                )}
              />
            </div>
          </div>
        </div>
        {isAdmin && (
          <div className="flex items-center justify-between py-2">
            <Button
              variant="primary"
              size="lg"
              onClick={(e) => {
                void handleSubmit(onSubmit)(e);
              }}
              loading={isLoading}
            >
              {isLoading ? t("updating") : t("workspace_settings.settings.general.update_workspace")}
            </Button>
          </div>
        )}
      </div>
    </>
  );
});

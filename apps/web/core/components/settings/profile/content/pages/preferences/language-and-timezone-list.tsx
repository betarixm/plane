/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { SUPPORTED_LANGUAGES, useTranslation } from "@plane/i18n";
import { getIdentitySourceDescriptor } from "@plane/constants";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { CustomSelect } from "@plane/ui";
// components
import { StartOfWeekPreference } from "@/components/profile/start-of-week-preference";
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
import { useUser, useUserProfile } from "@/hooks/store/user";

export const ProfileSettingsLanguageAndTimezonePreferencesList = observer(
  function ProfileSettingsLanguageAndTimezonePreferencesList() {
    // store hooks
    const {
      data: user,
      userProfile: { data: profile },
    } = useUser();
    const { updateUserProfile } = useUserProfile();
    const { config } = useInstance();
    const identitySource = config?.identity_source;
    const descriptor = identitySource ? getIdentitySourceDescriptor(identitySource.provider) : undefined;
    // translation
    const { t } = useTranslation();

    const handleLanguageChange = async (value: string) => {
      try {
        await updateUserProfile({ language: value });
        setToast({
          title: "Success!",
          message: "Language updated successfully",
          type: TOAST_TYPE.SUCCESS,
        });
      } catch (_error) {
        setToast({
          title: "Error!",
          message: "Failed to update language",
          type: TOAST_TYPE.ERROR,
        });
      }
    };

    const getLanguageLabel = (value: string) => {
      const selectedLanguage = SUPPORTED_LANGUAGES.find((l) => l.value === value);
      if (!selectedLanguage) return value;
      return selectedLanguage.label;
    };

    return (
      <div className="flex flex-col gap-y-1">
        <SettingsControlItem
          title={t("timezone")}
          description={`Managed by ${descriptor?.label ?? "your identity source"}`}
          control={
            <div className="min-w-48 rounded-md border border-subtle bg-surface-2 px-3 py-2 text-body-xs-regular text-tertiary">
              {user?.user_timezone || "UTC"}
            </div>
          }
        />
        <SettingsControlItem
          title={t("language")}
          description={t("language_setting")}
          control={
            <CustomSelect
              value={profile?.language}
              label={profile?.language ? getLanguageLabel(profile?.language) : "Select a language"}
              onChange={handleLanguageChange}
              buttonClassName="border border-subtle-1"
              className="rounded-md"
              input
              placement="bottom-end"
            >
              {SUPPORTED_LANGUAGES.map((item) => (
                <CustomSelect.Option key={item.value} value={item.value}>
                  {item.label}
                </CustomSelect.Option>
              ))}
            </CustomSelect>
          }
        />
        <StartOfWeekPreference
          option={{
            title: "First day of the week",
            description: "This will change how all calendars in your app look.",
          }}
        />
      </div>
    );
  }
);

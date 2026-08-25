/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import { useParams } from "next/navigation";

const useIntegrationPopup = ({
  provider,
  github_app_name,
}: {
  provider: string | undefined;
  github_app_name?: string;
}) => {
  const [authLoader, setAuthLoader] = useState(false);

  const { workspaceSlug } = useParams();

  const providerUrls: { [key: string]: string } = {
    github: `https://github.com/apps/${github_app_name}/installations/new?state=${workspaceSlug?.toString()}`,
  };

  const popup = useRef<any>();

  const checkPopup = () => {
    const check = setInterval(() => {
      if (!popup || popup.current.closed || popup.current.closed === undefined) {
        clearInterval(check);
        setAuthLoader(false);
      }
    }, 1000);
  };

  const openPopup = () => {
    if (!provider) return;

    const width = 600,
      height = 600;
    const left = window.innerWidth / 2 - width / 2;
    const top = window.innerHeight / 2 - height / 2;
    const url = providerUrls[provider];
    if (!url) return;

    return window.open(url, "", `width=${width}, height=${height}, top=${top}, left=${left}`);
  };

  const startAuth = () => {
    popup.current = openPopup();
    checkPopup();
    setAuthLoader(true);
  };

  return {
    startAuth,
    isConnecting: authLoader,
  };
};

export default useIntegrationPopup;

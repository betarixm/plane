# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from plane.app.views import BaseAPIView
from plane.db.models import IdentitySource
from plane.integrations.identity import (
    configured_identity_provider,
    identity_provider_adapter,
)
from plane.license.models import Instance
from plane.license.utils.instance_value import get_configuration_value
from plane.utils.identity_access import is_workspace_admin


class InstanceEndpoint(BaseAPIView):
    permission_classes = [AllowAny]

    @method_decorator(cache_control(private=True, max_age=12))
    def get(self, request):
        instance = Instance.objects.first()
        instance_data = {"is_setup_done": bool(instance and instance.is_setup_done)}
        (
            github_app_name,
            unsplash_access_key,
            llm_api_key,
        ) = get_configuration_value(
            [
                {"key": "GITHUB_APP_NAME", "default": os.environ.get("GITHUB_APP_NAME", "")},
                {"key": "UNSPLASH_ACCESS_KEY", "default": os.environ.get("UNSPLASH_ACCESS_KEY", "")},
                {"key": "LLM_API_KEY", "default": os.environ.get("LLM_API_KEY", "")},
            ]
        )

        configured_provider = configured_identity_provider()
        provider = configured_provider
        source = IdentitySource.objects.filter(provider=provider).first()
        provider_adapter = identity_provider_adapter(provider)
        identity_source = {
            "provider": provider,
            "configured": bool(
                provider == configured_provider
                and provider_adapter is not None
                and provider_adapter.credentials_configured()
            ),
            "connected": bool(
                source is not None
                and source.status == IdentitySource.Status.ACTIVE
            ),
            "organization": (
                {
                    "name": source.external_organization_name,
                    "domain": source.external_organization_domain,
                    "icon_url": source.external_organization_icon_url,
                }
                if source is not None
                else None
            ),
            "last_synced_at": source.last_synced_at if source is not None else None,
            "auth_url": provider_adapter.auth_url if provider_adapter is not None else "",
            "install_url": provider_adapter.install_url if provider_adapter is not None else "",
        }
        if source is not None and is_workspace_admin(request.user):
            identity_source["sync_error"] = source.sync_error
        config = {
            # Provider credentials, organization IDs, and tokens remain private.
            "identity_source": identity_source,
            # GitHub project integration is independent from human authentication.
            "github_app_name": github_app_name,
            "has_unsplash_configured": bool(unsplash_access_key),
            "has_llm_configured": bool(llm_api_key),
            "file_size_limit": float(os.environ.get("FILE_SIZE_LIMIT", 5242880)),
            "instance_changelog_url": settings.INSTANCE_CHANGELOG_URL,
            "is_self_managed": settings.IS_SELF_MANAGED,
        }
        return Response(
            {"config": config, "instance": instance_data},
            status=status.HTTP_200_OK,
        )

# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid
from urllib.parse import urlencode, urljoin

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.text import slugify
from django.views import View
from zxcvbn import zxcvbn

from plane.authentication.adapter.error import (
    AUTHENTICATION_ERROR_CODES,
    AuthenticationException,
)
from plane.authentication.utils.host import base_host
from plane.authentication.utils.login import user_login
from plane.bgtasks.workspace_seed_task import workspace_seed
from plane.db.models import Profile, User, Workspace, WorkspaceMember
from plane.license.models import Instance
from plane.utils.cache import invalidate_cache
from plane.utils.constants import RESTRICTED_WORKSPACE_SLUGS
from plane.utils.ip_address import get_client_ip
from plane.utils.workspace_admin import WORKSPACE_ADMIN_ROLE
from plane.utils.workspace_name import validate_workspace_name


def _workspace_slug(company_name):
    """Build the initial workspace slug without asking setup for another ID."""

    slug = slugify(company_name)[:48]
    if not slug or slug in RESTRICTED_WORKSPACE_SLUGS:
        slug = "workspace"
    return slug


def _setup_error_redirect(
    request,
    *,
    error_code,
    error_message,
    payload=None,
):
    exc = AuthenticationException(
        error_code=AUTHENTICATION_ERROR_CODES[error_code],
        error_message=error_message,
        payload=payload or {},
    )
    return HttpResponseRedirect(
        urljoin(
            base_host(request=request, is_admin=True),
            "?" + urlencode(exc.get_error_dict()),
        )
    )


class InstanceSetupEndpoint(View):
    """Initialize the instance, its only workspace, and its first administrator."""

    @invalidate_cache(path="/api/instances/", user=False)
    def post(self, request):
        instance = Instance.objects.first()
        if instance is None:
            return _setup_error_redirect(
                request,
                error_code="INSTANCE_NOT_CONFIGURED",
                error_message="INSTANCE_NOT_CONFIGURED",
            )

        if instance.is_setup_done or Workspace.all_objects.exists():
            return _setup_error_redirect(
                request,
                error_code="AUTHENTICATION_FAILED",
                error_message="INSTANCE_ALREADY_SETUP",
            )

        email = request.POST.get("email", False)
        password = request.POST.get("password", False)
        first_name = request.POST.get("first_name", False)
        last_name = request.POST.get("last_name", "")
        raw_company_name = request.POST.get("company_name", "")
        is_telemetry_enabled = str(request.POST.get("is_telemetry_enabled", "True")).lower() not in {"false", "0"}

        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "company_name": raw_company_name,
            "is_telemetry_enabled": is_telemetry_enabled,
        }

        if not email or not password or not first_name or not raw_company_name:
            return _setup_error_redirect(
                request,
                error_code="AUTHENTICATION_FAILED",
                error_message="REQUIRED_SETUP_FIELDS",
                payload=payload,
            )

        try:
            company_name = validate_workspace_name(raw_company_name)
        except ValidationError:
            return _setup_error_redirect(
                request,
                error_code="AUTHENTICATION_FAILED",
                error_message="INVALID_WORKSPACE_NAME",
                payload=payload,
            )
        payload["company_name"] = company_name

        email = email.strip().lower()
        payload["email"] = email
        try:
            validate_email(email)
        except ValidationError:
            return _setup_error_redirect(
                request,
                error_code="INVALID_EMAIL",
                error_message="INVALID_EMAIL",
                payload=payload,
            )

        if User.objects.filter(email=email).exists():
            return _setup_error_redirect(
                request,
                error_code="USER_ALREADY_EXIST",
                error_message="USER_ALREADY_EXIST",
                payload=payload,
            )

        if zxcvbn(password)["score"] < 3:
            return _setup_error_redirect(
                request,
                error_code="PASSWORD_TOO_WEAK",
                error_message="PASSWORD_TOO_WEAK",
                payload=payload,
            )

        with transaction.atomic():
            instance = Instance.objects.select_for_update().get(pk=instance.pk)
            if instance.is_setup_done or Workspace.all_objects.exists():
                return _setup_error_redirect(
                    request,
                    error_code="AUTHENTICATION_FAILED",
                    error_message="INSTANCE_ALREADY_SETUP",
                )

            user = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=uuid.uuid4().hex,
                password=make_password(password),
                is_password_autoset=False,
            )
            Profile.objects.create(user=user, company_name=company_name)
            user.is_active = True
            user.last_active = timezone.now()
            user.last_login_time = timezone.now()
            user.last_login_ip = get_client_ip(request=request)
            user.last_login_uagent = request.META.get("HTTP_USER_AGENT", "")
            user.token_updated_at = timezone.now()
            user.save()

            workspace = Workspace.objects.create(
                name=company_name,
                slug=_workspace_slug(company_name),
                owner=user,
            )
            WorkspaceMember.objects.create(
                workspace=workspace,
                member=user,
                role=WORKSPACE_ADMIN_ROLE,
            )
            instance.is_setup_done = True
            instance.instance_name = company_name
            instance.is_telemetry_enabled = is_telemetry_enabled
            instance.save()

            transaction.on_commit(lambda workspace_id=workspace.id: workspace_seed.delay(workspace_id))

        user_login(request=request, user=user)
        return HttpResponseRedirect(urljoin(base_host(request=request, is_admin=True), "general/"))

# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from contextlib import contextmanager
from functools import wraps

# Provider-neutral access queries and write fences for the singleton workspace.

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.db.models import Exists, F, OuterRef

from plane.db.models import (
    Project,
    ProjectMember,
    ExternalIdentity,
    IdentitySource,
    Workspace,
    WorkspaceMember,
)

WORKSPACE_ADMIN_ROLE = 20
WORKSPACE_MEMBER_ROLE = 15
WORKSPACE_GUEST_ROLE = 5
IDENTITY_SOURCE_ID_SESSION_KEY = "_identity_source_id"
IDENTITY_SOURCE_GENERATION_SESSION_KEY = "_identity_source_generation"
VALID_PROJECT_ROLES = frozenset(
    {
        WORKSPACE_ADMIN_ROLE,
        WORKSPACE_MEMBER_ROLE,
        WORKSPACE_GUEST_ROLE,
    }
)


def active_workspace_admins():
    """Return externally-backed administrators of the singleton workspace."""

    return active_workspace_members().filter(
        role=WORKSPACE_ADMIN_ROLE,
    )


def active_external_identities():
    """Return live identities from the currently active external source."""

    return ExternalIdentity.objects.using("default").filter(
        deleted_at__isnull=True,
        is_active=True,
        user__is_active=True,
        source__deleted_at__isnull=True,
        source__status=IdentitySource.Status.ACTIVE,
        source__workspace__deleted_at__isnull=True,
        source_generation=F("source__generation"),
        user__member_workspace__workspace=F("source__workspace"),
        user__member_workspace__deleted_at__isnull=True,
        user__member_workspace__is_active=True,
    )


def has_active_external_identity(user) -> bool:
    """Return whether ``user`` is projected by the active external source."""

    if not user or not user.is_authenticated or not user.is_active:
        return False
    return active_external_identities().filter(user_id=user.pk).exists()


def has_session_bound_external_identity(
    user,
    *,
    source_id,
    source_generation: int,
) -> bool:
    """Return whether a session belongs to the exact active source generation."""

    if not user or not user.is_authenticated or not user.is_active:
        return False
    return active_external_identities().filter(
        user_id=user.pk,
        source_id=source_id,
        source_generation=source_generation,
        source__generation=source_generation,
    ).exists()


def active_workspace_members():
    """Return human workspace memberships projected by the active source."""

    return WorkspaceMember.objects.using("default").filter(
        deleted_at__isnull=True,
        is_active=True,
        workspace__deleted_at__isnull=True,
        member__is_active=True,
        member__external_identity__deleted_at__isnull=True,
        member__external_identity__is_active=True,
        member__external_identity__source__deleted_at__isnull=True,
        member__external_identity__source__status=IdentitySource.Status.ACTIVE,
        member__external_identity__source__workspace=F("workspace"),
        member__external_identity__source_generation=F(
            "member__external_identity__source__generation"
        ),
    )


def active_project_members():
    """Return active project memberships backed by the external roster."""

    current_workspace_membership = active_workspace_members().filter(
        workspace_id=OuterRef("workspace_id"),
        member_id=OuterRef("member_id"),
    )
    return (
        ProjectMember.objects.using("default")
        .filter(
            deleted_at__isnull=True,
            is_active=True,
            project__deleted_at__isnull=True,
            project__workspace_id=F("workspace_id"),
        )
        .alias(
            _has_current_external_workspace_membership=Exists(
                current_workspace_membership
            )
        )
        .filter(_has_current_external_workspace_membership=True)
    )


def lock_active_identity_source(*, workspace_id):
    """Lock the authoritative source for an externally-owned mutation.

    The caller must be inside ``transaction.atomic()`` and keep the lock until
    every dependent local projection has been written. Provider synchronization
    takes this same lock first, preventing a role downgrade from racing a
    project-role or project-lead write.
    """

    return IdentitySource.objects.using("default").select_for_update().get(
        workspace_id=workspace_id,
        workspace__deleted_at__isnull=True,
        deleted_at__isnull=True,
        status=IdentitySource.Status.ACTIVE,
    )


def lock_active_workspace_member(*, workspace_id, user_id):
    """Lock and return a member from the source's current generation.

    Callers must lock the active identity source first. Re-checking the
    requester through this queryset prevents an already-authenticated request
    from retaining authority across a source reconnect or roster change.
    """

    return (
        active_workspace_members()
        .select_for_update()
        .filter(
            workspace_id=workspace_id,
            member_id=user_id,
        )
        .only("id", "workspace_id", "member_id", "role")
        .first()
    )


@contextmanager
def identity_workspace_write_fence(*, workspace_id, user_id, allowed_roles=None):
    """Linearize an externally-owned workspace write with roster synchronization.

    The identity source row is deliberately the first row lock in the
    transaction.  Serializers must be validated and saved inside this context;
    Provider sync uses the same source-first order, so a reconnect, removal,
    or role change cannot land between target validation and persistence.
    """

    with transaction.atomic():
        try:
            source = lock_active_identity_source(
                workspace_id=workspace_id
            )
        except IdentitySource.DoesNotExist as exc:
            raise PermissionDenied(
                "An active external identity source is required."
            ) from exc
        workspace_member = lock_active_workspace_member(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if workspace_member is None or (
            allowed_roles is not None
            and workspace_member.role not in frozenset(allowed_roles)
        ):
            raise PermissionDenied(
                "An active current external workspace membership is required."
            )
        yield source, workspace_member


@contextmanager
def identity_project_write_fence(
    *, workspace_id, project_id, user_id, allowed_roles=None
):
    """Linearize a project write and re-check the actor under the source fence."""

    with identity_workspace_write_fence(
        workspace_id=workspace_id,
        user_id=user_id,
    ) as (source, workspace_member):
        if not Project.objects.using("default").filter(
            pk=project_id,
            workspace_id=workspace_id,
            deleted_at__isnull=True,
        ).exists():
            raise Http404
        project_member = (
            active_project_members()
            .select_for_update()
            .filter(
                workspace_id=workspace_id,
                project_id=project_id,
                member_id=user_id,
            )
            .only("id", "workspace_id", "project_id", "member_id", "role")
            .first()
        )
        if project_member is None or (
            allowed_roles is not None
            and project_member.role not in frozenset(allowed_roles)
        ):
            raise PermissionDenied(
                "An active current external project membership is required."
            )
        yield source, workspace_member, project_member


def identity_project_write_fenced(*, allowed_roles=None):
    """Decorate a project mutation with a source-first write fence."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(instance, request, *args, **kwargs):
            workspace_id = (
                Workspace.objects.using("default").filter(
                    slug=kwargs["slug"],
                    deleted_at__isnull=True,
                )
                .values_list("id", flat=True)
                .first()
            )
            if workspace_id is None:
                raise Http404
            if not Project.objects.using("default").filter(
                pk=kwargs["project_id"],
                workspace_id=workspace_id,
                deleted_at__isnull=True,
            ).exists():
                raise Http404
            with identity_project_write_fence(
                workspace_id=workspace_id,
                project_id=kwargs["project_id"],
                user_id=request.user.id,
                allowed_roles=allowed_roles,
            ):
                return view_func(instance, request, *args, **kwargs)

        return wrapped

    return decorator


def enqueue_task_after_commit(task, *args, **kwargs):
    """Publish a background task only after the surrounding write commits."""

    def _enqueue():
        task.delay(*args, **kwargs)

    transaction.on_commit(_enqueue, robust=True)


def lock_current_session_identity(
    *,
    source_id,
    expected_generation: int,
    user_id,
):
    """Lock and revalidate the external projection before persisting a session.

    The caller must be inside ``transaction.atomic()`` and keep the returned
    source fence until the session write is complete.
    """

    source = (
        IdentitySource.objects.using("default")
        .select_for_update()
        .filter(
            pk=source_id,
            deleted_at__isnull=True,
            status=IdentitySource.Status.ACTIVE,
            generation=expected_generation,
            workspace__deleted_at__isnull=True,
        )
        .first()
    )
    if source is None:
        return None

    identity = (
        ExternalIdentity.objects.using("default")
        .select_for_update()
        .select_related("user")
        .filter(
            source=source,
            source_generation=expected_generation,
            user_id=user_id,
            deleted_at__isnull=True,
            is_active=True,
            user__is_active=True,
        )
        .first()
    )
    if identity is None:
        return None
    if not WorkspaceMember.objects.using("default").select_for_update().filter(
        workspace_id=source.workspace_id,
        member_id=user_id,
        deleted_at__isnull=True,
        is_active=True,
    ).exists():
        return None
    return identity


def is_workspace_admin(user):
    """Return whether a user holds unified workspace/instance authority."""

    if not user or not user.is_authenticated:
        return False
    return active_workspace_admins().filter(member=user).exists()


def project_role_for_workspace_role(*, workspace_role: int, requested_role: int) -> int:
    """Apply the external workspace-role ceiling/floor to a project role."""

    if requested_role not in VALID_PROJECT_ROLES:
        raise ValueError("Invalid project role")
    if workspace_role == WORKSPACE_ADMIN_ROLE:
        return WORKSPACE_ADMIN_ROLE
    if workspace_role == WORKSPACE_GUEST_ROLE:
        return WORKSPACE_GUEST_ROLE
    return requested_role

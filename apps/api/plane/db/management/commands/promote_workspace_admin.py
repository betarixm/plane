# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management.base import BaseCommand, CommandError

from plane.db.models import User, Workspace, WorkspaceMember
from plane.utils.workspace_admin import (
    WORKSPACE_ADMIN_ROLE,
    workspace_admin_guard,
)


class Command(BaseCommand):
    help = "Promote a user to administrator of the singleton workspace"

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Workspace administrator email")

    def handle(self, *args, **options):
        email = options.get("email", "").strip().lower()
        if not email:
            raise CommandError("Please provide the administrator email.")

        user = User.objects.filter(email=email).first()
        if user is None:
            raise CommandError("User with the provided email does not exist.")
        if user.is_bot or not user.is_active:
            raise CommandError("Only active human users can be administrators.")

        workspace = Workspace.objects.first()
        if workspace is None:
            raise CommandError("The workspace is not configured yet.")

        try:
            with workspace_admin_guard(workspace_id=workspace.id) as locked_workspace:
                workspace_member, _ = WorkspaceMember.objects.update_or_create(
                    workspace=locked_workspace,
                    member=user,
                    defaults={"role": WORKSPACE_ADMIN_ROLE, "is_active": True},
                )
                if workspace_member.role == WORKSPACE_ADMIN_ROLE:
                    self.stdout.write(self.style.SUCCESS("Successfully promoted the workspace administrator"))
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError("Failed to promote the workspace administrator.") from exc

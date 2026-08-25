# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from typing import Any

from django.core.management.base import BaseCommand, CommandError

# Module imports
from plane.db.models import User, Workspace
from plane.utils.identity_access import active_workspace_members


class Command(BaseCommand):
    help = "Create dummy issues, cycles, and projects in the singleton workspace"

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            workspace = Workspace.objects.first()
            if workspace is None:
                raise CommandError("The workspace is not configured yet")
            workspace_slug = workspace.slug

            creator = input("Your email: ")

            if creator == "" or not User.objects.filter(email=creator).exists():
                raise CommandError("User email is required and should have signed in plane")

            user = User.objects.get(email=creator)
            if not active_workspace_members().filter(
                workspace=workspace,
                member=user,
            ).exists():
                raise CommandError("The creator must be an active external workspace member")

            members = input("Enter Member emails (comma separated): ")
            members = [email.strip().lower() for email in members.split(",") if email.strip()]
            active_member_emails = set(
                active_workspace_members().filter(
                    workspace=workspace,
                    member__email__in=members,
                ).values_list("member__email", flat=True)
            )
            missing_members = sorted(set(members) - active_member_emails)
            if missing_members:
                raise CommandError(
                    "Every dummy-data member must already be an active external workspace member: "
                    + ", ".join(missing_members)
                )

            project_count = int(input("Number of projects to be created: "))

            for i in range(project_count):
                print(f"Please provide the following details for project {i + 1}:")
                issue_count = int(input("Number of issues to be created: "))
                cycle_count = int(input("Number of cycles to be created: "))
                module_count = int(input("Number of modules to be created: "))
                intake_issue_count = int(input("Number of intake issues to be created: "))

                from plane.bgtasks.dummy_data_task import create_dummy_data

                create_dummy_data(
                    slug=workspace_slug,
                    email=creator,
                    members=members,
                    issue_count=issue_count,
                    cycle_count=cycle_count,
                    module_count=module_count,
                    intake_issue_count=intake_issue_count,
                )

            self.stdout.write(self.style.SUCCESS("Data is pushed to the queue"))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Command errored out {str(e)}"))
            return

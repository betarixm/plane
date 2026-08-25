# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from plane.license.models import Instance


def create_instance(**overrides):
    values = {
        "instance_name": "Plane Community Edition",
        "instance_id": uuid4().hex,
        "current_version": "test",
        "last_checked_at": timezone.now(),
    }
    values.update(overrides)
    return Instance.objects.create(**values)


@pytest.mark.unit
@pytest.mark.django_db
class TestInstanceModel:
    def test_second_instance_is_rejected_by_database(self):
        instance = create_instance()

        with pytest.raises(IntegrityError), transaction.atomic():
            create_instance()

        assert Instance.all_objects.get() == instance

    def test_singleton_instance_cannot_be_deleted_or_soft_deleted(self):
        instance = create_instance()

        with pytest.raises(ValidationError, match="cannot be deleted"):
            instance.delete()
        with pytest.raises(ValidationError, match="cannot be deleted"):
            Instance.objects.filter(pk=instance.pk).delete()
        with pytest.raises(ValidationError, match="cannot be deleted"):
            Instance.all_objects.filter(pk=instance.pk).delete()
        with pytest.raises(IntegrityError), transaction.atomic():
            Instance.all_objects.filter(pk=instance.pk).update(deleted_at=timezone.now())

        assert Instance.objects.get() == instance

    def test_register_instance_is_idempotent(self, monkeypatch):
        from plane.license.management.commands import register_instance

        command = register_instance.Command()
        monkeypatch.setattr(command, "check_for_current_version", lambda: "v1")
        monkeypatch.setattr(
            command,
            "check_for_latest_version",
            lambda fallback_version: fallback_version,
        )
        monkeypatch.setattr(register_instance.push_instance_metrics, "delay", lambda: None)

        command.handle(machine_signature="first-replica")
        registered = Instance.objects.get()
        command.handle(machine_signature="second-replica")

        assert Instance.objects.get() == registered
        assert Instance.objects.count() == 1

# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("license", "0009_instance_singleton"),
    ]

    operations = [
        migrations.DeleteModel(name="InstanceConfiguration"),
    ]

# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os


def get_configuration_value(keys):
    """Read deployment configuration exclusively from the process environment."""

    return tuple(os.environ.get(key["key"], key.get("default")) for key in keys)

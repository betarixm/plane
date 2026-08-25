# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging
import os
import uuid
from typing import Any, Dict

# third party imports
from celery import shared_task
from posthog import Posthog

# module imports
from plane.license.utils.instance_value import get_configuration_value
from plane.utils.exception_logger import log_exception

logger = logging.getLogger("plane.worker")


def posthogConfiguration():
    POSTHOG_API_KEY, POSTHOG_HOST = get_configuration_value(
        [
            {
                "key": "POSTHOG_API_KEY",
                "default": os.environ.get("POSTHOG_API_KEY", None),
            },
            {
                "key": "POSTHOG_HOST",
                "default": os.environ.get("POSTHOG_HOST", None),
            },
        ]
    )
    if POSTHOG_API_KEY and POSTHOG_HOST:
        return POSTHOG_API_KEY, POSTHOG_HOST
    else:
        return None, None


@shared_task
def track_event(user_id: uuid.UUID, event_name: str, slug: str, event_properties: Dict[str, Any]):
    POSTHOG_API_KEY, POSTHOG_HOST = posthogConfiguration()

    if not (POSTHOG_API_KEY and POSTHOG_HOST):
        logger.warning("Event tracking is not configured")
        return

    try:
        data_properties = event_properties
        groups = {
            "workspace": slug,
        }
        # track the event using posthog
        posthog = Posthog(POSTHOG_API_KEY, host=POSTHOG_HOST)
        posthog.capture(distinct_id=str(user_id), event=event_name, properties=data_properties, groups=groups)
    except Exception as e:
        log_exception(e)
        return False

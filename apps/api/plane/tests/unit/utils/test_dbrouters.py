# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import patch
from types import SimpleNamespace

import pytest

from plane.utils.core.dbrouters import ReadReplicaRouter

pytestmark = pytest.mark.unit


def model_with_label(label: str):
    class Model:
        _meta = SimpleNamespace(label_lower=label, label=label)

    return Model


@pytest.mark.parametrize(
    "label",
    [
        "db.apitoken",
        "db.externalidentity",
        "db.identitysource",
        "db.projectmember",
        "db.session",
        "db.slackeventreceipt",
        "db.slackusertombstone",
        "db.user",
        "db.workspacemember",
    ],
)
@patch("plane.utils.core.dbrouters.should_use_read_replica", return_value=True)
def test_security_sensitive_models_always_read_from_primary(mock_should_use_replica, label):
    database = ReadReplicaRouter().db_for_read(model_with_label(label))

    assert database == "default"
    mock_should_use_replica.assert_not_called()


@patch("plane.utils.core.dbrouters.should_use_read_replica", return_value=True)
def test_regular_models_can_still_read_from_replica(mock_should_use_replica):
    database = ReadReplicaRouter().db_for_read(model_with_label("db.issue"))

    assert database == "replica"
    mock_should_use_replica.assert_called_once_with()

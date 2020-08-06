from pathlib import Path

import pytest  # noqa: F401

from mvt import _utils


def test_():
    fixtures_path = Path(__file__).parent.joinpath('fixtures')
    # TODO: Actual data comparison
    assert _utils.get_renovate_config(fixtures_path)

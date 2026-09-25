# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The installed distribution and the exported source version must agree."""
from importlib.metadata import version

from szl_triage import __version__


def test_installed_distribution_matches_exported_version():
    assert version("szl-triage") == __version__

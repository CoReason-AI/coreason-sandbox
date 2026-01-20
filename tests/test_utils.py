# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

import importlib
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from coreason_sandbox.utils import logger


def test_logger_initialization_in_clean_env() -> None:
    """
    Test that the logger initialization code correctly creates the 'logs' directory
    in a clean environment where it does not exist.
    """
    with TemporaryDirectory() as temp_dir:
        # To prevent side effects with other tests, we run this in an isolated
        # temporary directory.
        os.chdir(temp_dir)

        # Force a reload of the logger module to re-trigger the initialization
        # logic within the temporary directory.
        importlib.reload(logger)

        log_path = Path("logs")
        assert log_path.exists(), "The 'logs' directory was not created."
        assert log_path.is_dir()

        # Clean up the created directory to avoid interfering with other tests
        shutil.rmtree(log_path)


def test_logger_exports() -> None:
    """Test that logger is exported."""
    assert logger is not None

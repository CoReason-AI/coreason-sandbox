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
import shutil
from pathlib import Path

from fda_orange_book.utils import logger as logger_module
from fda_orange_book.utils.logger import logger


def test_logger_initialization() -> None:
    """Test that the logger is initialized correctly and creates the log directory."""
    log_path = Path("logs")

    # The logger is initialized on the first import.
    # We test both cases: when the directory exists and when it does not.

    # 1. Test the case where the directory does not exist.
    # We need to remove it first.
    if log_path.exists():
        shutil.rmtree(log_path)

    # Now, reload the logger module to trigger the directory creation.
    importlib.reload(logger_module)
    assert log_path.exists()
    assert log_path.is_dir()

    # 2. Test the case where the directory already exists.
    # The directory was created in the previous step.
    # Reloading again should not cause an error.
    importlib.reload(logger_module)
    assert log_path.exists()
    assert log_path.is_dir()


def test_logger_exports() -> None:
    """Test that logger is exported."""
    assert logger is not None

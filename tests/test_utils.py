# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

import shutil
from pathlib import Path

from coreason_sandbox.utils.logger import logger, setup_logging


def test_logger_initialization() -> None:
    """Test that the logger is initialized correctly and creates the log directory."""
    log_path = Path("logs")
    assert log_path.exists()
    assert log_path.is_dir()

def test_logger_exports() -> None:
    """Test that logger is exported."""
    assert logger is not None

def test_log_directory_creation(tmp_path):
    """Test that the logs directory is created if it doesn't exist."""
    # Temporarily remove the logs directory
    logs_dir = Path("logs")
    if logs_dir.exists():
        shutil.rmtree(logs_dir)

    # Re-run the logging setup, which should re-create the directory
    setup_logging()

    # Assert that the directory and file now exist
    assert logs_dir.exists()
    assert logs_dir.is_dir()
    assert Path("logs/app.log").exists()

    # Clean up by removing the logs directory again
    if logs_dir.exists():
        shutil.rmtree(logs_dir)
    
    # Restore the original logging setup
    setup_logging()

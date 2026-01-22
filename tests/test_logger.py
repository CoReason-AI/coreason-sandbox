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
import logging
from pathlib import Path
import shutil

# This import is intentionally module-level to test initial setup
import coreason_sandbox.utils.logger as logger_module


def test_logger_initialization_and_directory_creation():
    """
    Verify that the logger is initialized correctly and creates the logs directory.
    """
    # GIVEN the logger module is imported

    # WHEN we check the file system
    log_dir = Path("logs")

    # THEN the logs directory should exist
    assert log_dir.is_dir()

    # and a log file should have been created
    log_files = list(log_dir.glob("app.log*"))
    assert len(log_files) > 0

    # and the logger should have two sinks configured (stderr and file)
    # Note: Accessing internal attributes like this is for testing purposes.
    assert len(logger_module.logger._core.handlers) == 2

    # Cleanup: remove the created logs directory for a clean state
    shutil.rmtree(log_dir)


def test_logger_reloading():
    """
    Verify that reloading the logger module re-runs the setup logic.
    """
    # GIVEN the logs directory does not exist
    log_dir = Path("logs")
    if log_dir.exists():
        shutil.rmtree(log_dir)
    assert not log_dir.exists()

    # WHEN the logger module is reloaded
    importlib.reload(logger_module)

    # THEN the logs directory should be created again
    assert log_dir.is_dir()

    # Cleanup
    shutil.rmtree(log_dir)


def test_logger_sink_configuration(capsys):
    """
    Verify the logger's sinks are configured as expected.
    """
    # GIVEN a fresh import of the logger
    log_dir = Path("logs")
    if log_dir.exists():
        shutil.rmtree(log_dir)
    importlib.reload(logger_module)

    # WHEN we log a message
    test_message = "This is a test message."
    logger_module.logger.info(test_message)

    # THEN the message should appear in stderr
    captured = capsys.readouterr()
    assert test_message in captured.err

    # AND the message should be written to the log file (in JSON format)
    # We must remove the logger to ensure the async file sink is flushed before reading.
    logger_module.logger.remove()

    log_file = log_dir / "app.log"
    with open(log_file, "r") as f:
        log_content = f.read()
    assert '"message": "' + test_message + '"' in log_content

    # Cleanup
    shutil.rmtree(log_dir)

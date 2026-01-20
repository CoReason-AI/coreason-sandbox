# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from pathlib import Path

from coreason_sandbox.utils.logger import logger


def test_logger_initialization() -> None:
    """Test that the logger is initialized correctly and creates the log directory."""
    # Since the logger is initialized on import, we check side effects

    # Check if logs directory creation is handled
    # Note: running this test might actually create the directory in the test environment
    # if it doesn't exist.

    log_path = Path("logs")
    assert log_path.exists()
    assert log_path.is_dir()

    # Verify app.log creation if it was logged to (it might be empty or not created until log)
    # logger.info("Test log")
    # assert (log_path / "app.log").exists()

def test_log_directory_creation() -> None:
    """
    Test that the log directory is created if it does not exist.
    """
    log_path = Path("logs")
    if log_path.exists():
        import shutil
        shutil.rmtree(log_path)

    # Reload the logger module to trigger the directory creation
    import importlib
    from coreason_sandbox.utils import logger as logger_module
    importlib.reload(logger_module)

    assert log_path.exists()
    assert log_path.is_dir()

    # Clean up
    if log_path.exists():
        import shutil
        shutil.rmtree(log_path)
    
    importlib.reload(logger_module)


def test_logger_exports() -> None:
    """Test that logger is exported."""
    assert logger is not None

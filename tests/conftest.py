from typing import Any, Generator
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_global_veritas() -> Generator[Any, None, None]:
    """
    Globally mock VeritasIntegrator to prevent OpenTelemetry connection errors
    and loguru 'I/O operation on closed file' errors during test teardown.
    """
    with patch("coreason_sandbox.utils.veritas.IERLogger", None):
        yield

# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

"""Tests for the runtime factory and configuration."""

import pytest
from pydantic import ValidationError

from coreason_sandbox import DockerRuntime, E2BRuntime, SandboxConfig, get_runtime


def test_default_runtime_is_docker(monkeypatch):
    """Test that the default runtime is Docker when no env var is set."""
    monkeypatch.delenv("SANDBOX_RUNTIME", raising=False)
    monkeypatch.delenv("SANDBOX_E2B_API_KEY", raising=False)
    runtime = get_runtime()
    assert isinstance(runtime, DockerRuntime)


def test_docker_runtime_selected(monkeypatch):
    """Test that the Docker runtime is selected when explicitly configured."""
    monkeypatch.setenv("SANDBOX_RUNTIME", "docker")
    runtime = get_runtime()
    assert isinstance(runtime, DockerRuntime)


def test_e2b_runtime_selected(monkeypatch):
    """Test that the E2B runtime is selected when configured and key is present."""
    monkeypatch.setenv("SANDBOX_RUNTIME", "e2b")
    monkeypatch.setenv("SANDBOX_E2B_API_KEY", "test_api_key")
    runtime = get_runtime()
    assert isinstance(runtime, E2BRuntime)


def test_e2b_runtime_raises_error_if_no_api_key(monkeypatch):
    """Test that a ValueError is raised if E2B is selected but no key is set."""
    monkeypatch.setenv("SANDBOX_RUNTIME", "e2b")
    monkeypatch.delenv("SANDBOX_E2B_API_KEY", raising=False)
    with pytest.raises(ValueError, match="E2B_API_KEY must be set"):
        get_runtime()


def test_invalid_runtime_raises_error(monkeypatch):
    """Test that a Pydantic ValidationError is raised for an invalid RUNTIME."""
    monkeypatch.setenv("SANDBOX_RUNTIME", "invalid_runtime")
    with pytest.raises(ValidationError):
        SandboxConfig()

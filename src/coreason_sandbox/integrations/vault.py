# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from typing import Protocol, runtime_checkable

from loguru import logger


@runtime_checkable
class VaultClientProtocol(Protocol):
    """
    Protocol for Vault Client to allow dependency injection and testing.
    """

    def get_secret(self, key: str) -> str | None:
        """
        Retrieve a secret by key.
        """
        ...


class VaultIntegrator:
    """
    Integrates with coreason-vault to fetch secrets.
    Falls back to None if vault is unavailable.
    """

    def __init__(self, client: VaultClientProtocol | None = None):
        self.client = client
        if not self.client:
            try:
                # Attempt to import the real client if available in the environment
                from coreason_vault import VaultClient

                self.client = VaultClient()
            except ImportError:
                logger.warning(
                    "coreason-vault not found or not installed. Secrets will be loaded from environment variables."
                )

    def get_secret(self, key: str) -> str | None:
        """
        Fetch a secret from the vault.
        Returns None if client is missing or fetch fails.
        """
        if self.client:
            try:
                return self.client.get_secret(key)
            except Exception as e:
                logger.warning(f"Failed to fetch secret {key} from Vault: {e}")
        return None

import os
from typing import Protocol, runtime_checkable

from loguru import logger


class VaultIntegrator:
    """
    Simplified Integrator: Directly reads from Environment Variables.
    Removes dependency on coreason-vault.
    """

    def __init__(self, client=None):
        # Client is ignored in standalone mode
        pass

    def get_secret(self, key: str) -> str | None:
        """
        Fetch secret directly from Environment Variables.
        """
        # Map Vault keys to Env Vars if necessary, or just read direct
        val = os.getenv(key)
        if not val:
            # Try with prefix if standard naming convention is used
            val = os.getenv(f"COREASON_SANDBOX_{key}")

        if not val:
            logger.debug(f"Secret {key} not found in environment.")

        return val

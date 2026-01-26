import hashlib

from loguru import logger


class VeritasIntegrator:
    """Standalone Integrator for audit logging.

    Logs execution attempts to STDOUT (local mode) to remove external dependencies.
    """

    def __init__(self, service_name: str = "coreason-sandbox", enabled: bool = True):
        """Initializes the VeritasIntegrator.

        Args:
            service_name: The name of the service (default: 'coreason-sandbox').
            enabled: Whether to enable audit logging.
        """
        self.enabled = enabled
        if self.enabled:
            logger.info("Veritas Audit Logging enabled (Local Mode - STDOUT only)")

    async def log_pre_execution(self, code: str, language: str) -> str:
        """Log the code execution attempt.

        Calculates a SHA-256 hash of the code and logs it if enabled.

        Args:
            code: The code to be executed.
            language: The programming language of the code.

        Returns:
            str: The SHA-256 hash of the code.
        """
        code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        if self.enabled:
            # Log to standard logger instead of external auditor
            logger.info(f"AUDIT: Executing {language} code. Hash: {code_hash}, Length: {len(code)}")
        return code_hash

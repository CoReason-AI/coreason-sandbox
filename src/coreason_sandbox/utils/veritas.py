import hashlib

from loguru import logger

# Try importing IERLogger
try:
    from coreason_veritas.auditor import IERLogger
except ImportError:
    IERLogger = None  # type: ignore
    logger.warning("IERLogger not found in coreason_veritas. Audit logging disabled.")


class VeritasIntegrator:
    """
    Integrates with coreason-veritas for audit logging.
    """

    def __init__(self, service_name: str = "coreason-sandbox", enabled: bool = True):
        # Only enable if config says YES and library is present
        self.enabled = enabled and (IERLogger is not None)

        if self.enabled:
            try:
                self.logger = IERLogger(service_name=service_name)
            except Exception as e:
                logger.warning(f"Failed to initialize Veritas IERLogger: {e}")
                self.enabled = False

    async def log_pre_execution(self, code: str, language: str) -> str:
        """
        Log the code execution attempt. Returns a hash of the code.
        """
        # Generate hash
        code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

        if self.enabled:
            try:
                await self.logger.log_event(
                    event_type="SANDBOX_EXECUTION_START",
                    details={
                        "language": language,
                        "code_hash": code_hash,
                        "code_length": len(code),
                    },
                )
            except Exception as e:
                logger.error(f"Veritas logging failed: {e}")

        return code_hash

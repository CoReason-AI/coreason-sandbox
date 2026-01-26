import hashlib

from loguru import logger


class VeritasIntegrator:
    """
    Standalone Integrator: Audit logging is disabled or logs to stdout.
    Removes dependency on coreason-veritas.
    """

    def __init__(self, service_name: str = "coreason-sandbox", enabled: bool = True):
        self.enabled = enabled
        if self.enabled:
            logger.info("Veritas Audit Logging enabled (Local Mode - STDOUT only)")

    async def log_pre_execution(self, code: str, language: str) -> str:
        """
        Log the code execution attempt to local logs.
        """
        code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        if self.enabled:
            # Log to standard logger instead of external auditor
            logger.info(f"AUDIT: Executing {language} code. Hash: {code_hash}, Length: {len(code)}")
        return code_hash

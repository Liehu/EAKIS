"""EAKIS exception hierarchy.

All custom exceptions inherit from EAKISBaseError which carries a
human-readable message, a machine-readable code, and an HTTP status
that can be used directly by API error handlers.
"""


class EAKISBaseError(Exception):
    """Root exception for every EAKIS domain error."""

    code: str = "EAKIS_ERROR"
    http_status: int = 500

    def __init__(self, message: str, code: str | None = None, http_status: int | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        super().__init__(self.message)


# -- Resource not-found errors (404) -----------------------------------------

class TaskNotFoundError(EAKISBaseError):
    code = "TASK_NOT_FOUND"
    http_status = 404


class AssetNotFoundError(EAKISBaseError):
    code = "ASSET_NOT_FOUND"
    http_status = 404


# -- External-service errors (500) -------------------------------------------

class LLMError(EAKISBaseError):
    code = "LLM_ERROR"
    http_status = 500


class CrawlerError(EAKISBaseError):
    code = "CRAWLER_ERROR"
    http_status = 500


# -- Configuration / startup errors (500) ------------------------------------

class ConfigurationError(EAKISBaseError):
    code = "CONFIGURATION_ERROR"
    http_status = 500


# -- Auth errors (401) -------------------------------------------------------

class AuthenticationError(EAKISBaseError):
    code = "AUTHENTICATION_ERROR"
    http_status = 401


# -- Rate-limiting (429) -----------------------------------------------------

class RateLimitExceededError(EAKISBaseError):
    code = "RATE_LIMIT_EXCEEDED"
    http_status = 429


# -- Persistence errors (500) ------------------------------------------------

class StorageError(EAKISBaseError):
    code = "STORAGE_ERROR"
    http_status = 500


# -- Resilience / circuit-breaker (503) --------------------------------------

class CircuitOpenError(EAKISBaseError):
    code = "CIRCUIT_OPEN"
    http_status = 503


# -- Input validation (400) --------------------------------------------------

class ValidationError(EAKISBaseError):
    code = "VALIDATION_ERROR"
    http_status = 400


# -- Pipeline orchestration (500) --------------------------------------------

class PipelineError(EAKISBaseError):
    code = "PIPELINE_ERROR"
    http_status = 500

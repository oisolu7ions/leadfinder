"""Provider-specific exceptions."""


class ProviderNotConfiguredError(Exception):
    """Raised when a live provider is used without required configuration."""


class ProviderAPIError(Exception):
    """Raised when an external provider API returns an error."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

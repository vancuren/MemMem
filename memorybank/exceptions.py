"""Exception classes for MemoryBank SDK."""

class MemoryBankError(Exception):
    """Base exception for all MemoryBank errors."""
    pass

class AuthenticationError(MemoryBankError):
    """Raised when authentication fails."""
    pass

class ConfigurationError(MemoryBankError):
    """Raised when configuration is invalid or missing."""
    pass

class APIError(MemoryBankError):
    """Raised when API requests fail."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code

class EmbeddingError(MemoryBankError):
    """Raised when embedding generation fails."""
    pass

class VectorStoreError(MemoryBankError):
    """Raised when vector store operations fail."""
    pass

class LLMError(MemoryBankError):
    """Raised when LLM operations fail."""
    pass
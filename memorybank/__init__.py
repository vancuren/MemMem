"""
MemoryBank SDK - Long-term memory system for conversational AI agents.

A MemoryBank-inspired external long-term memory system that provides:
- Persistent memory storage using vector embeddings
- Intelligent retrieval with semantic search
- Automatic forgetting using Ebbinghaus curve
- Multi-LLM support (Claude, OpenAI, Google Gemini)
- Easy integration with existing applications
"""

__version__ = "0.1.0"
__author__ = "MemoryBank Development Team"
__email__ = "support@memorybank.dev"

from .client import MemoryBankClient, AsyncMemoryBankClient
from .config import MemoryBankConfig
from .models import Memory, MemoryMetadata, QueryResult
from .exceptions import MemoryBankError, AuthenticationError, ConfigurationError

__all__ = [
    "MemoryBankClient",
    "AsyncMemoryBankClient", 
    "MemoryBankConfig",
    "Memory",
    "MemoryMetadata",
    "QueryResult",
    "MemoryBankError",
    "AuthenticationError",
    "ConfigurationError",
]
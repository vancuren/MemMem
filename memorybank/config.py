"""Configuration management for MemoryBank SDK."""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import os
from pathlib import Path
import json

from .exceptions import ConfigurationError

@dataclass
class MemoryBankConfig:
    """Configuration for MemoryBank client."""
    
    # API Configuration
    api_key: Optional[str] = None
    base_url: str = "http://localhost:8000"
    timeout: int = 30
    
    # LLM Configuration
    llm_provider: str = "claude"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Embedding Configuration
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-ada-002"
    
    # Memory Configuration
    default_top_k: int = 5
    importance_threshold: float = 0.1
    
    # Local Storage (for offline mode)
    local_db_path: Optional[str] = None
    enable_local_storage: bool = False
    
    # Advanced Settings
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_logging: bool = True
    log_level: str = "INFO"
    
    # Additional settings
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls) -> "MemoryBankConfig":
        """Create configuration from environment variables."""
        return cls(
            api_key=os.getenv("MEMORYBANK_API_KEY"),
            base_url=os.getenv("MEMORYBANK_BASE_URL", "http://localhost:8000"),
            timeout=int(os.getenv("MEMORYBANK_TIMEOUT", "30")),
            
            llm_provider=os.getenv("MEMORYBANK_LLM_PROVIDER", "claude"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            
            embedding_provider=os.getenv("MEMORYBANK_EMBEDDING_PROVIDER", "openai"),
            embedding_model=os.getenv("MEMORYBANK_EMBEDDING_MODEL", "text-embedding-ada-002"),
            
            default_top_k=int(os.getenv("MEMORYBANK_DEFAULT_TOP_K", "5")),
            importance_threshold=float(os.getenv("MEMORYBANK_IMPORTANCE_THRESHOLD", "0.1")),
            
            local_db_path=os.getenv("MEMORYBANK_LOCAL_DB_PATH"),
            enable_local_storage=os.getenv("MEMORYBANK_ENABLE_LOCAL_STORAGE", "false").lower() == "true",
            
            max_retries=int(os.getenv("MEMORYBANK_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("MEMORYBANK_RETRY_DELAY", "1.0")),
            enable_logging=os.getenv("MEMORYBANK_ENABLE_LOGGING", "true").lower() == "true",
            log_level=os.getenv("MEMORYBANK_LOG_LEVEL", "INFO"),
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> "MemoryBankConfig":
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return cls(**config_data)
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except TypeError as e:
            raise ConfigurationError(f"Invalid configuration parameters: {e}")
    
    def to_file(self, config_path: str) -> None:
        """Save configuration to JSON file."""
        config_dict = {}
        for key, value in self.__dict__.items():
            if value is not None:
                config_dict[key] = value
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def validate(self) -> None:
        """Validate the configuration."""
        if not self.enable_local_storage and not self.api_key:
            raise ConfigurationError("API key is required when not using local storage")
        
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ConfigurationError("OpenAI API key is required for OpenAI LLM provider")
        
        if self.llm_provider == "claude" and not self.anthropic_api_key:
            raise ConfigurationError("Anthropic API key is required for Claude LLM provider")
        
        if self.llm_provider == "gemini" and not self.google_api_key:
            raise ConfigurationError("Google API key is required for Gemini LLM provider")
        
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ConfigurationError("OpenAI API key is required for OpenAI embedding provider")
        
        if self.default_top_k < 1:
            raise ConfigurationError("default_top_k must be at least 1")
        
        if not 0 <= self.importance_threshold <= 1:
            raise ConfigurationError("importance_threshold must be between 0 and 1")
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM-specific configuration."""
        config = {
            "provider": self.llm_provider,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
        }
        
        if self.llm_provider == "openai":
            config["api_key"] = self.openai_api_key
        elif self.llm_provider == "claude":
            config["api_key"] = self.anthropic_api_key
        elif self.llm_provider == "gemini":
            config["api_key"] = self.google_api_key
        
        return config
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """Get embedding-specific configuration."""
        config = {
            "provider": self.embedding_provider,
            "model": self.embedding_model,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
        }
        
        if self.embedding_provider == "openai":
            config["api_key"] = self.openai_api_key
        
        return config
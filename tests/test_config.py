"""Tests for MemoryBank configuration."""

import pytest
import tempfile
import os
import json
from memorybank.config import MemoryBankConfig
from memorybank.exceptions import ConfigurationError

class TestMemoryBankConfig:
    """Test configuration management."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MemoryBankConfig()
        
        assert config.base_url == "http://localhost:8000"
        assert config.timeout == 30
        assert config.llm_provider == "claude"
        assert config.embedding_provider == "openai"
        assert config.default_top_k == 5
        assert config.importance_threshold == 0.1
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.enable_logging is True
        assert config.log_level == "INFO"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = MemoryBankConfig(
            api_key="test-key",
            base_url="https://api.example.com",
            timeout=60,
            llm_provider="openai",
            default_top_k=10
        )
        
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.example.com"
        assert config.timeout == 60
        assert config.llm_provider == "openai"
        assert config.default_top_k == 10
    
    def test_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("MEMORYBANK_API_KEY", "env-api-key")
        monkeypatch.setenv("MEMORYBANK_BASE_URL", "https://env.example.com")
        monkeypatch.setenv("MEMORYBANK_LLM_PROVIDER", "gemini")
        monkeypatch.setenv("MEMORYBANK_DEFAULT_TOP_K", "15")
        
        config = MemoryBankConfig.from_env()
        
        assert config.api_key == "env-api-key"
        assert config.base_url == "https://env.example.com"
        assert config.llm_provider == "gemini"
        assert config.default_top_k == 15
    
    def test_to_file_and_from_file(self):
        """Test saving and loading configuration from file."""
        original_config = MemoryBankConfig(
            api_key="file-test-key",
            base_url="https://file.example.com",
            llm_provider="claude",
            default_top_k=7
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            # Save config
            original_config.to_file(config_path)
            
            # Load config
            loaded_config = MemoryBankConfig.from_file(config_path)
            
            assert loaded_config.api_key == original_config.api_key
            assert loaded_config.base_url == original_config.base_url
            assert loaded_config.llm_provider == original_config.llm_provider
            assert loaded_config.default_top_k == original_config.default_top_k
            
        finally:
            os.unlink(config_path)
    
    def test_from_file_not_found(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            MemoryBankConfig.from_file("nonexistent.json")
    
    def test_from_file_invalid_json(self):
        """Test error with invalid JSON in config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            config_path = f.name
        
        try:
            with pytest.raises(ConfigurationError, match="Invalid JSON"):
                MemoryBankConfig.from_file(config_path)
        finally:
            os.unlink(config_path)
    
    def test_validate_success(self):
        """Test successful validation."""
        config = MemoryBankConfig(
            api_key="test-key",
            llm_provider="claude",
            anthropic_api_key="claude-key",
            embedding_provider="openai",
            openai_api_key="openai-key"
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_validate_missing_api_key(self):
        """Test validation failure when API key is missing."""
        config = MemoryBankConfig(enable_local_storage=False)
        
        with pytest.raises(ConfigurationError, match="API key is required"):
            config.validate()
    
    def test_validate_missing_llm_key(self):
        """Test validation failure when LLM provider key is missing."""
        config = MemoryBankConfig(
            api_key="test-key",
            llm_provider="claude"
            # Missing anthropic_api_key
        )
        
        with pytest.raises(ConfigurationError, match="Anthropic API key is required"):
            config.validate()
    
    def test_validate_invalid_top_k(self):
        """Test validation failure with invalid top_k."""
        config = MemoryBankConfig(
            api_key="test-key",
            default_top_k=0
        )
        
        with pytest.raises(ConfigurationError, match="default_top_k must be at least 1"):
            config.validate()
    
    def test_validate_invalid_threshold(self):
        """Test validation failure with invalid importance threshold."""
        config = MemoryBankConfig(
            api_key="test-key",
            importance_threshold=1.5
        )
        
        with pytest.raises(ConfigurationError, match="importance_threshold must be between 0 and 1"):
            config.validate()
    
    def test_get_llm_config(self):
        """Test LLM configuration extraction."""
        config = MemoryBankConfig(
            llm_provider="claude",
            anthropic_api_key="claude-key",
            timeout=60,
            max_retries=5
        )
        
        llm_config = config.get_llm_config()
        
        assert llm_config["provider"] == "claude"
        assert llm_config["api_key"] == "claude-key"
        assert llm_config["timeout"] == 60
        assert llm_config["max_retries"] == 5
    
    def test_get_embedding_config(self):
        """Test embedding configuration extraction."""
        config = MemoryBankConfig(
            embedding_provider="openai",
            embedding_model="text-embedding-ada-002",
            openai_api_key="openai-key",
            timeout=30
        )
        
        embedding_config = config.get_embedding_config()
        
        assert embedding_config["provider"] == "openai"
        assert embedding_config["model"] == "text-embedding-ada-002"
        assert embedding_config["api_key"] == "openai-key"
        assert embedding_config["timeout"] == 30
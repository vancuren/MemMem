"""Tests for MemoryBank data models."""

import pytest
from datetime import datetime
from memorybank.models import (
    MemoryMetadata, Memory, QueryResult, ChatMessage, ChatResponse, MemoryStats
)

class TestMemoryMetadata:
    """Test MemoryMetadata model."""
    
    def test_default_metadata(self):
        """Test default metadata creation."""
        metadata = MemoryMetadata()
        
        assert metadata.user_id is None
        assert metadata.session_id is None
        assert metadata.category is None
        assert metadata.tags == []
        assert metadata.custom_fields == {}
    
    def test_custom_metadata(self):
        """Test metadata with custom values."""
        metadata = MemoryMetadata(
            user_id="user123",
            session_id="session456",
            category="preference",
            tags=["tag1", "tag2"],
            custom_fields={"importance": "high", "source": "chat"}
        )
        
        assert metadata.user_id == "user123"
        assert metadata.session_id == "session456"
        assert metadata.category == "preference"
        assert metadata.tags == ["tag1", "tag2"]
        assert metadata.custom_fields["importance"] == "high"
        assert metadata.custom_fields["source"] == "chat"
    
    def test_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = MemoryMetadata(
            user_id="user123",
            category="test",
            tags=["a", "b"],
            custom_fields={"extra": "value"}
        )
        
        result = metadata.to_dict()
        
        assert result["user_id"] == "user123"
        assert result["category"] == "test"
        assert result["tags"] == ["a", "b"]
        assert result["extra"] == "value"
        assert "session_id" not in result  # Should not include None values
    
    def test_from_dict(self):
        """Test creating metadata from dictionary."""
        data = {
            "user_id": "user456",
            "category": "hobby",
            "tags": ["music", "guitar"],
            "custom_field": "custom_value",
            "priority": 5
        }
        
        metadata = MemoryMetadata.from_dict(data)
        
        assert metadata.user_id == "user456"
        assert metadata.category == "hobby"
        assert metadata.tags == ["music", "guitar"]
        assert metadata.custom_fields["custom_field"] == "custom_value"
        assert metadata.custom_fields["priority"] == 5

class TestMemory:
    """Test Memory model."""
    
    def test_memory_creation(self):
        """Test memory creation with required fields."""
        timestamp = datetime.now()
        metadata = MemoryMetadata(user_id="user123", category="test")
        
        memory = Memory(
            memory_id="mem123",
            content="Test memory content",
            metadata=metadata,
            timestamp=timestamp
        )
        
        assert memory.memory_id == "mem123"
        assert memory.content == "Test memory content"
        assert memory.metadata == metadata
        assert memory.timestamp == timestamp
        assert memory.last_accessed is None
        assert memory.importance == 1.0
        assert memory.access_count == 0
    
    def test_memory_to_dict(self):
        """Test converting memory to dictionary."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        metadata = MemoryMetadata(user_id="user123")
        
        memory = Memory(
            memory_id="mem123",
            content="Test content",
            metadata=metadata,
            timestamp=timestamp,
            importance=0.8,
            access_count=5
        )
        
        result = memory.to_dict()
        
        assert result["memory_id"] == "mem123"
        assert result["content"] == "Test content"
        assert result["timestamp"] == "2024-01-01T12:00:00"
        assert result["importance"] == 0.8
        assert result["access_count"] == 5
        assert result["metadata"]["user_id"] == "user123"
    
    def test_memory_from_dict(self):
        """Test creating memory from dictionary."""
        data = {
            "memory_id": "mem456",
            "content": "Another test",
            "timestamp": "2024-01-01T12:00:00",
            "importance": 0.9,
            "access_count": 3,
            "metadata": {"user_id": "user456", "category": "test"}
        }
        
        memory = Memory.from_dict(data)
        
        assert memory.memory_id == "mem456"
        assert memory.content == "Another test"
        assert memory.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert memory.importance == 0.9
        assert memory.access_count == 3
        assert memory.metadata.user_id == "user456"
        assert memory.metadata.category == "test"

class TestQueryResult:
    """Test QueryResult model."""
    
    def test_query_result_creation(self):
        """Test query result creation."""
        memory = Memory(
            memory_id="mem123",
            content="Test memory",
            metadata=MemoryMetadata(user_id="user123"),
            timestamp=datetime.now()
        )
        
        result = QueryResult(memory=memory, score=0.85)
        
        assert result.memory == memory
        assert result.score == 0.85
    
    def test_query_result_to_dict(self):
        """Test converting query result to dictionary."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        memory = Memory(
            memory_id="mem123",
            content="Test memory",
            metadata=MemoryMetadata(user_id="user123"),
            timestamp=timestamp
        )
        
        result = QueryResult(memory=memory, score=0.75)
        result_dict = result.to_dict()
        
        assert result_dict["score"] == 0.75
        assert result_dict["memory"]["memory_id"] == "mem123"
        assert result_dict["memory"]["content"] == "Test memory"

class TestChatMessage:
    """Test ChatMessage model."""
    
    def test_chat_message_creation(self):
        """Test chat message creation."""
        message = ChatMessage(
            role="user",
            content="Hello, how are you?"
        )
        
        assert message.role == "user"
        assert message.content == "Hello, how are you?"
        assert isinstance(message.timestamp, datetime)
        assert isinstance(message.metadata, MemoryMetadata)
    
    def test_chat_message_to_dict(self):
        """Test converting chat message to dictionary."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        metadata = MemoryMetadata(user_id="user123")
        
        message = ChatMessage(
            role="assistant",
            content="I'm doing well, thank you!",
            timestamp=timestamp,
            metadata=metadata
        )
        
        result = message.to_dict()
        
        assert result["role"] == "assistant"
        assert result["content"] == "I'm doing well, thank you!"
        assert result["timestamp"] == "2024-01-01T12:00:00"
        assert result["metadata"]["user_id"] == "user123"

class TestChatResponse:
    """Test ChatResponse model."""
    
    def test_chat_response_creation(self):
        """Test chat response creation."""
        memory = Memory(
            memory_id="mem123",
            content="Test memory",
            metadata=MemoryMetadata(),
            timestamp=datetime.now()
        )
        
        query_result = QueryResult(memory=memory, score=0.8)
        
        response = ChatResponse(
            response="This is the response",
            model_used="claude-3-sonnet",
            memories_used=[query_result],
            message_stored=True,
            memory_id="new_mem_id"
        )
        
        assert response.response == "This is the response"
        assert response.model_used == "claude-3-sonnet"
        assert len(response.memories_used) == 1
        assert response.message_stored is True
        assert response.memory_id == "new_mem_id"

class TestMemoryStats:
    """Test MemoryStats model."""
    
    def test_memory_stats_creation(self):
        """Test memory stats creation."""
        oldest = datetime(2024, 1, 1)
        newest = datetime(2024, 1, 31)
        
        stats = MemoryStats(
            total_memories=100,
            avg_importance=0.75,
            oldest_memory=oldest,
            newest_memory=newest,
            embedding_provider="openai"
        )
        
        assert stats.total_memories == 100
        assert stats.avg_importance == 0.75
        assert stats.oldest_memory == oldest
        assert stats.newest_memory == newest
        assert stats.embedding_provider == "openai"
    
    def test_memory_stats_from_dict(self):
        """Test creating memory stats from dictionary."""
        data = {
            "total_memories": 50,
            "avg_importance": 0.6,
            "oldest_memory": "2024-01-01T00:00:00",
            "newest_memory": "2024-01-31T23:59:59",
            "embedding_provider": "openai"
        }
        
        stats = MemoryStats.from_dict(data)
        
        assert stats.total_memories == 50
        assert stats.avg_importance == 0.6
        assert stats.oldest_memory == datetime(2024, 1, 1)
        assert stats.newest_memory == datetime(2024, 1, 31, 23, 59, 59)
        assert stats.embedding_provider == "openai"
    
    def test_memory_stats_to_dict(self):
        """Test converting memory stats to dictionary."""
        oldest = datetime(2024, 1, 1)
        newest = datetime(2024, 1, 31)
        
        stats = MemoryStats(
            total_memories=25,
            avg_importance=0.8,
            oldest_memory=oldest,
            newest_memory=newest,
            embedding_provider="huggingface"
        )
        
        result = stats.to_dict()
        
        assert result["total_memories"] == 25
        assert result["avg_importance"] == 0.8
        assert result["oldest_memory"] == "2024-01-01T00:00:00"
        assert result["newest_memory"] == "2024-01-31T00:00:00"
        assert result["embedding_provider"] == "huggingface"
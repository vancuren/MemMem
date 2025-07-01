"""Data models for MemoryBank SDK."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

class LLMProvider(Enum):
    """Supported LLM providers."""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"

class EmbeddingProvider(Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"

@dataclass
class MemoryMetadata:
    """Metadata associated with a memory."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {}
        if self.user_id:
            result["user_id"] = self.user_id
        if self.session_id:
            result["session_id"] = self.session_id
        if self.category:
            result["category"] = self.category
        if self.tags:
            result["tags"] = self.tags
        result.update(self.custom_fields)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryMetadata":
        """Create from dictionary."""
        # Extract known fields
        user_id = data.get("user_id")
        session_id = data.get("session_id")
        category = data.get("category")
        tags = data.get("tags", [])
        
        # Everything else goes to custom_fields
        custom_fields = {k: v for k, v in data.items() 
                        if k not in ["user_id", "session_id", "category", "tags"]}
        
        return cls(
            user_id=user_id,
            session_id=session_id,
            category=category,
            tags=tags,
            custom_fields=custom_fields
        )

@dataclass
class Memory:
    """Represents a stored memory."""
    memory_id: str
    content: str
    metadata: MemoryMetadata
    timestamp: datetime
    last_accessed: Optional[datetime] = None
    importance: float = 1.0
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "importance": self.importance,
            "access_count": self.access_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create from dictionary."""
        timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        last_accessed = None
        if data.get("last_accessed"):
            last_accessed = datetime.fromisoformat(data["last_accessed"].replace('Z', '+00:00'))
        
        return cls(
            memory_id=data["memory_id"],
            content=data["content"],
            metadata=MemoryMetadata.from_dict(data.get("metadata", {})),
            timestamp=timestamp,
            last_accessed=last_accessed,
            importance=data.get("importance", 1.0),
            access_count=data.get("access_count", 0)
        )

@dataclass
class QueryResult:
    """Result from a memory query."""
    memory: Memory
    score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory": self.memory.to_dict(),
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryResult":
        """Create from dictionary."""
        return cls(
            memory=Memory.from_dict(data["memory"]),
            score=data["score"]
        )

@dataclass
class ChatMessage:
    """Represents a chat message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: MemoryMetadata = field(default_factory=MemoryMetadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata.to_dict()
        }

@dataclass
class ChatResponse:
    """Response from chat with memory."""
    response: str
    model_used: str
    memories_used: List[QueryResult]
    message_stored: bool = False
    memory_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "response": self.response,
            "model_used": self.model_used,
            "memories_used": [m.to_dict() for m in self.memories_used],
            "message_stored": self.message_stored,
            "memory_id": self.memory_id
        }

@dataclass
class MemoryStats:
    """Memory statistics."""
    total_memories: int
    avg_importance: float
    oldest_memory: Optional[datetime]
    newest_memory: Optional[datetime]
    embedding_provider: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_memories": self.total_memories,
            "avg_importance": self.avg_importance,
            "oldest_memory": self.oldest_memory.isoformat() if self.oldest_memory else None,
            "newest_memory": self.newest_memory.isoformat() if self.newest_memory else None,
            "embedding_provider": self.embedding_provider
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryStats":
        """Create from dictionary."""
        oldest = None
        if data.get("oldest_memory"):
            oldest = datetime.fromisoformat(data["oldest_memory"].replace('Z', '+00:00'))
        
        newest = None
        if data.get("newest_memory"):
            newest = datetime.fromisoformat(data["newest_memory"].replace('Z', '+00:00'))
        
        return cls(
            total_memories=data["total_memories"],
            avg_importance=data["avg_importance"],
            oldest_memory=oldest,
            newest_memory=newest,
            embedding_provider=data["embedding_provider"]
        )
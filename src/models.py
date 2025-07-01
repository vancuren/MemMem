from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class StoreMemoryRequest(BaseModel):
    content: str = Field(..., description="The memory content to store")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the memory")

class StoreMemoryResponse(BaseModel):
    memory_id: str = Field(..., description="Unique identifier for the stored memory")
    status: str = Field(..., description="Status of the storage operation")

class RetrieveMemoryRequest(BaseModel):
    query: str = Field(..., description="Query text to search for relevant memories")
    top_k: int = Field(default=3, description="Number of top memories to retrieve")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters for retrieval")

class MemoryItem(BaseModel):
    memory_id: str = Field(..., description="Unique identifier of the memory")
    content: str = Field(..., description="The memory content")
    timestamp: str = Field(..., description="When the memory was created")
    score: float = Field(..., description="Relevance score for the query")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Memory metadata")

class RetrieveMemoryResponse(BaseModel):
    memories: List[MemoryItem] = Field(..., description="List of retrieved memories")

class ForgetMemoryRequest(BaseModel):
    memory_id: str = Field(..., description="ID of the memory to forget/delete")

class ForgetMemoryResponse(BaseModel):
    status: str = Field(..., description="Status of the forget operation")
    memory_id: str = Field(..., description="ID of the forgotten memory")

class Memory(BaseModel):
    memory_id: str
    content: str
    embedding: List[float]
    timestamp: datetime
    last_accessed: datetime
    importance: float
    access_count: int
    metadata: Dict[str, Any]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class LLMRequest(BaseModel):
    query: str = Field(..., description="User's query/message")
    context: Optional[str] = Field(default=None, description="Additional context")
    model: Optional[str] = Field(default=None, description="Specific model to use")
    system_prompt: Optional[str] = Field(default=None, description="System prompt for the LLM")

class LLMResponse(BaseModel):
    response: str = Field(..., description="LLM's response")
    model_used: str = Field(..., description="Model that generated the response")
    memories_used: List[MemoryItem] = Field(default_factory=list, description="Memories that were used in the response")
"""Main client classes for MemoryBank SDK."""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import httpx

from .config import MemoryBankConfig
from .models import (
    Memory, MemoryMetadata, QueryResult, ChatMessage, ChatResponse, MemoryStats
)
from .exceptions import (
    MemoryBankError, AuthenticationError, APIError, ConfigurationError
)

logger = logging.getLogger(__name__)

class BaseMemoryBankClient:
    """Base class for MemoryBank clients."""
    
    def __init__(self, config: Optional[MemoryBankConfig] = None):
        """Initialize the client with configuration."""
        self.config = config or MemoryBankConfig.from_env()
        self.config.validate()
        
        # Set up logging
        if self.config.enable_logging:
            logging.basicConfig(level=getattr(logging, self.config.log_level.upper()))
        
        # Set up headers
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": f"MemoryBank-SDK/0.1.0",
            **self.config.custom_headers
        }
        
        if self.config.api_key:
            self.headers["Authorization"] = f"Bearer {self.config.api_key}"

class AsyncMemoryBankClient(BaseMemoryBankClient):
    """Async client for MemoryBank API."""
    
    def __init__(self, config: Optional[MemoryBankConfig] = None):
        """Initialize the async client."""
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=self.headers
            )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request with retry logic."""
        await self._ensure_client()
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self._client.request(method, endpoint, **kwargs)
                
                if response.status_code == 401:
                    raise AuthenticationError("Invalid API key or authentication failed")
                
                if response.status_code >= 400:
                    error_msg = f"API request failed with status {response.status_code}"
                    try:
                        error_detail = response.json().get("detail", error_msg)
                        error_msg = error_detail
                    except:
                        pass
                    raise APIError(error_msg, response.status_code)
                
                return response.json()
                
            except httpx.RequestError as e:
                if attempt == self.config.max_retries:
                    raise MemoryBankError(f"Request failed after {self.config.max_retries + 1} attempts: {e}")
                
                # Wait before retry
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
        
        raise MemoryBankError("Request failed after all retry attempts")
    
    async def store_memory(
        self, 
        content: str, 
        metadata: Optional[MemoryMetadata] = None
    ) -> str:
        """Store a new memory.
        
        Args:
            content: The memory content to store
            metadata: Optional metadata for the memory
            
        Returns:
            The ID of the stored memory
        """
        request_data = {
            "content": content,
            "metadata": metadata.to_dict() if metadata else {}
        }
        
        response = await self._request("POST", "/store_memory", json=request_data)
        return response["memory_id"]
    
    async def retrieve_memories(
        self,
        query: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[MemoryMetadata] = None
    ) -> List[QueryResult]:
        """Retrieve relevant memories for a query.
        
        Args:
            query: The search query
            top_k: Number of memories to retrieve (default from config)
            metadata_filter: Optional metadata filter
            
        Returns:
            List of relevant memories with scores
        """
        request_data = {
            "query": query,
            "top_k": top_k or self.config.default_top_k,
            "metadata": metadata_filter.to_dict() if metadata_filter else {}
        }
        
        response = await self._request("POST", "/retrieve_memory", json=request_data)
        
        results = []
        for memory_data in response["memories"]:
            # Convert API response to our models
            memory = Memory(
                memory_id=memory_data["memory_id"],
                content=memory_data["content"],
                metadata=MemoryMetadata.from_dict(memory_data.get("metadata", {})),
                timestamp=datetime.fromisoformat(memory_data["timestamp"].replace('Z', '+00:00')),
                importance=memory_data.get("importance", 1.0),
                access_count=memory_data.get("access_count", 0)
            )
            
            result = QueryResult(memory=memory, score=memory_data["score"])
            results.append(result)
        
        return results
    
    async def forget_memory(self, memory_id: str) -> bool:
        """Delete a memory.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            True if successfully deleted
        """
        request_data = {"memory_id": memory_id}
        
        try:
            response = await self._request("POST", "/forget_memory", json=request_data)
            return response["status"] == "deleted"
        except APIError as e:
            if e.status_code == 404:
                return False
            raise
    
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        store_conversation: bool = True,
        metadata: Optional[MemoryMetadata] = None
    ) -> ChatResponse:
        """Chat with memory-augmented LLM.
        
        Args:
            message: User message
            system_prompt: Optional system prompt
            model: Optional specific model to use
            store_conversation: Whether to store the conversation in memory
            metadata: Optional metadata for stored memories
            
        Returns:
            Chat response with used memories
        """
        request_data = {
            "query": message,
            "system_prompt": system_prompt,
            "model": model
        }
        
        response = await self._request("POST", "/chat", json=request_data)
        
        # Convert memories to QueryResult objects
        memories_used = []
        for memory_data in response.get("memories_used", []):
            memory = Memory(
                memory_id=memory_data["memory_id"],
                content=memory_data["content"],
                metadata=MemoryMetadata.from_dict(memory_data.get("metadata", {})),
                timestamp=datetime.fromisoformat(memory_data["timestamp"].replace('Z', '+00:00')),
                importance=memory_data.get("importance", 1.0),
                access_count=memory_data.get("access_count", 0)
            )
            result = QueryResult(memory=memory, score=memory_data["score"])
            memories_used.append(result)
        
        return ChatResponse(
            response=response["response"],
            model_used=response["model_used"],
            memories_used=memories_used,
            message_stored=store_conversation
        )
    
    async def get_memory_stats(self) -> MemoryStats:
        """Get memory statistics.
        
        Returns:
            Memory statistics
        """
        response = await self._request("GET", "/memory_stats")
        return MemoryStats.from_dict(response)
    
    async def run_forgetting_curve(self) -> Dict[str, Any]:
        """Manually run the forgetting curve.
        
        Returns:
            Results of the forgetting curve application
        """
        return await self._request("POST", "/run_forgetting_curve")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health.
        
        Returns:
            Health status
        """
        return await self._request("GET", "/health")

class MemoryBankClient(BaseMemoryBankClient):
    """Synchronous client for MemoryBank API."""
    
    def __init__(self, config: Optional[MemoryBankConfig] = None):
        """Initialize the sync client."""
        super().__init__(config)
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[AsyncMemoryBankClient] = None
    
    def __enter__(self):
        """Context manager entry."""
        self._ensure_client()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=self.headers
            )
    
    def _ensure_async_client(self):
        """Ensure async client is initialized."""
        if self._async_client is None:
            self._async_client = AsyncMemoryBankClient(self.config)
    
    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None
    
    def _run_async(self, coro):
        """Run an async coroutine in sync context."""
        self._ensure_async_client()
        return asyncio.run(coro)
    
    def store_memory(
        self, 
        content: str, 
        metadata: Optional[MemoryMetadata] = None
    ) -> str:
        """Store a new memory (sync version)."""
        return self._run_async(self._async_client.store_memory(content, metadata))
    
    def retrieve_memories(
        self,
        query: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[MemoryMetadata] = None
    ) -> List[QueryResult]:
        """Retrieve relevant memories (sync version)."""
        return self._run_async(
            self._async_client.retrieve_memories(query, top_k, metadata_filter)
        )
    
    def forget_memory(self, memory_id: str) -> bool:
        """Delete a memory (sync version)."""
        return self._run_async(self._async_client.forget_memory(memory_id))
    
    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        store_conversation: bool = True,
        metadata: Optional[MemoryMetadata] = None
    ) -> ChatResponse:
        """Chat with memory-augmented LLM (sync version)."""
        return self._run_async(
            self._async_client.chat(
                message, system_prompt, model, store_conversation, metadata
            )
        )
    
    def get_memory_stats(self) -> MemoryStats:
        """Get memory statistics (sync version)."""
        return self._run_async(self._async_client.get_memory_stats())
    
    def run_forgetting_curve(self) -> Dict[str, Any]:
        """Manually run the forgetting curve (sync version)."""
        return self._run_async(self._async_client.run_forgetting_curve())
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health (sync version)."""
        return self._run_async(self._async_client.health_check())
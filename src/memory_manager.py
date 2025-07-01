from typing import List, Dict, Any, Optional
import logging
import os
from datetime import datetime

from .embedding_client import create_embedding_client, EmbeddingClient
from .vector_store import VectorStore
from .models import MemoryItem

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(
        self, 
        embedding_provider: str = None,
        db_path: str = None,
        collection_name: str = "long_term_memories"
    ):
        self.embedding_provider = embedding_provider or os.getenv("EMBEDDING_PROVIDER", "openai")
        self.db_path = db_path or os.getenv("CHROMA_DB_PATH", "./memory_db")
        
        self.embedding_client: EmbeddingClient = create_embedding_client(self.embedding_provider)
        self.vector_store = VectorStore(self.db_path, collection_name)
        
        logger.info(f"MemoryManager initialized with {self.embedding_provider} embeddings")
    
    async def store_memory(self, content: str, metadata: Dict[str, Any] = None) -> str:
        try:
            # Generate embedding for the content
            embedding = await self.embedding_client.embed(content)
            
            # Store in vector database
            memory_id = await self.vector_store.add_memory(content, embedding, metadata)
            
            logger.info(f"Successfully stored memory: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise
    
    async def retrieve_memory(
        self, 
        query: str, 
        top_k: int = 3, 
        metadata_filter: Dict[str, Any] = None
    ) -> List[MemoryItem]:
        try:
            # Generate embedding for the query
            query_embedding = await self.embedding_client.embed(query)
            
            # Search in vector database
            raw_memories = await self.vector_store.query_memories(
                query_embedding, 
                top_k=top_k,
                where=metadata_filter
            )
            
            # Convert to MemoryItem format
            memories = []
            for raw_memory in raw_memories:
                memory_item = MemoryItem(
                    memory_id=raw_memory["memory_id"],
                    content=raw_memory["content"],
                    timestamp=raw_memory["metadata"].get("timestamp", ""),
                    score=raw_memory["score"],
                    metadata=raw_memory["metadata"]
                )
                memories.append(memory_item)
            
            logger.info(f"Retrieved {len(memories)} memories for query: {query}")
            return memories
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            raise
    
    async def forget_memory(self, memory_id: str) -> bool:
        try:
            success = await self.vector_store.delete_memory(memory_id)
            if success:
                logger.info(f"Successfully forgot memory: {memory_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error forgetting memory {memory_id}: {e}")
            return False
    
    async def update_memory_importance(self, memory_id: str, importance: float) -> bool:
        try:
            success = await self.vector_store.update_memory_importance(memory_id, importance)
            if success:
                logger.info(f"Updated importance for memory {memory_id}: {importance}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating memory importance: {e}")
            return False
    
    async def prune_memories(self, importance_threshold: float = 0.1) -> int:
        try:
            deleted_count = await self.vector_store.prune_low_importance_memories(importance_threshold)
            logger.info(f"Pruned {deleted_count} memories below importance threshold {importance_threshold}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error pruning memories: {e}")
            return 0
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        try:
            all_memories = await self.vector_store.get_all_memories()
            total_memories = len(all_memories.get("ids", []))
            
            if total_memories == 0:
                return {
                    "total_memories": 0,
                    "avg_importance": 0,
                    "oldest_memory": None,
                    "newest_memory": None
                }
            
            importances = [
                metadata.get("importance", 1.0) 
                for metadata in all_memories.get("metadatas", [])
            ]
            
            timestamps = [
                metadata.get("timestamp", "") 
                for metadata in all_memories.get("metadatas", [])
                if metadata.get("timestamp")
            ]
            
            avg_importance = sum(importances) / len(importances) if importances else 0
            
            timestamps.sort()
            oldest_memory = timestamps[0] if timestamps else None
            newest_memory = timestamps[-1] if timestamps else None
            
            return {
                "total_memories": total_memories,
                "avg_importance": round(avg_importance, 3),
                "oldest_memory": oldest_memory,
                "newest_memory": newest_memory,
                "embedding_provider": self.embedding_provider
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, db_path: str = "./memory_db", collection_name: str = "long_term_memories"):
        self.db_path = db_path
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Initialized vector store at {db_path}")
    
    async def add_memory(
        self, 
        content: str, 
        embedding: List[float], 
        metadata: Dict[str, Any] = None
    ) -> str:
        memory_id = str(uuid.uuid4())
        
        memory_metadata = {
            "timestamp": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "importance": 1.0,
            "access_count": 0,
            **(metadata or {})
        }
        
        try:
            self.collection.add(
                documents=[content],
                embeddings=[embedding],
                ids=[memory_id],
                metadatas=[memory_metadata]
            )
            logger.info(f"Added memory with ID: {memory_id}")
            return memory_id
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            raise
    
    async def query_memories(
        self, 
        query_embedding: List[float], 
        top_k: int = 3,
        where: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            memories = []
            if results["ids"] and results["ids"][0]:
                for i, memory_id in enumerate(results["ids"][0]):
                    memory = {
                        "memory_id": memory_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "score": 1 - results["distances"][0][i]  # Convert distance to similarity
                    }
                    memories.append(memory)
                    
                    # Update access information
                    await self._update_access_info(memory_id, results["metadatas"][0][i])
            
            return memories
        except Exception as e:
            logger.error(f"Error querying memories: {e}")
            raise
    
    async def _update_access_info(self, memory_id: str, current_metadata: Dict[str, Any]):
        try:
            updated_metadata = current_metadata.copy()
            updated_metadata["last_accessed"] = datetime.now().isoformat()
            updated_metadata["access_count"] = updated_metadata.get("access_count", 0) + 1
            
            # Boost importance based on access frequency
            base_importance = updated_metadata.get("importance", 1.0)
            access_boost = min(0.1 * updated_metadata["access_count"], 0.5)
            updated_metadata["importance"] = min(base_importance + access_boost, 2.0)
            
            self.collection.update(
                ids=[memory_id],
                metadatas=[updated_metadata]
            )
        except Exception as e:
            logger.error(f"Error updating access info for memory {memory_id}: {e}")
    
    async def delete_memory(self, memory_id: str) -> bool:
        try:
            self.collection.delete(ids=[memory_id])
            logger.info(f"Deleted memory with ID: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False
    
    async def get_all_memories(self) -> Dict[str, Any]:
        try:
            return self.collection.get(include=["documents", "metadatas"])
        except Exception as e:
            logger.error(f"Error getting all memories: {e}")
            raise
    
    async def update_memory_importance(self, memory_id: str, new_importance: float):
        try:
            # Get current metadata
            result = self.collection.get(ids=[memory_id], include=["metadatas"])
            if not result["metadatas"]:
                return False
            
            current_metadata = result["metadatas"][0]
            current_metadata["importance"] = new_importance
            
            self.collection.update(
                ids=[memory_id],
                metadatas=[current_metadata]
            )
            return True
        except Exception as e:
            logger.error(f"Error updating memory importance: {e}")
            return False
    
    async def prune_low_importance_memories(self, threshold: float = 0.1) -> int:
        try:
            all_memories = await self.get_all_memories()
            deleted_count = 0
            
            for i, memory_id in enumerate(all_memories["ids"]):
                metadata = all_memories["metadatas"][i]
                if metadata.get("importance", 1.0) < threshold:
                    await self.delete_memory(memory_id)
                    deleted_count += 1
            
            logger.info(f"Pruned {deleted_count} low-importance memories")
            return deleted_count
        except Exception as e:
            logger.error(f"Error pruning memories: {e}")
            return 0
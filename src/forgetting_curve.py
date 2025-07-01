import math
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

class ForgettingCurve:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
    
    def calculate_retention_strength(
        self, 
        timestamp: str, 
        last_accessed: str, 
        access_count: int,
        base_importance: float = 1.0
    ) -> float:
        try:
            created_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            accessed_time = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))
            current_time = datetime.now()
            
            # Time since creation (in days)
            days_since_creation = (current_time - created_time).days
            
            # Time since last access (in days)
            days_since_access = (current_time - accessed_time).days
            
            # Ebbinghaus forgetting curve: R(t) = e^(-t/S)
            # Where R(t) is retention, t is time, S is strength
            
            # Base strength influenced by access frequency
            strength_factor = 1 + (access_count * 0.5)  # Each access increases strength
            
            # Calculate retention based on time since last access
            if days_since_access == 0:
                retention = 1.0
            else:
                retention = math.exp(-days_since_access / strength_factor)
            
            # Apply base importance multiplier
            final_importance = base_importance * retention
            
            # Ensure minimum decay over time
            age_decay = max(0.1, 1 - (days_since_creation * 0.01))  # 1% decay per day
            final_importance *= age_decay
            
            return max(0.0, min(2.0, final_importance))  # Clamp between 0 and 2
            
        except Exception as e:
            logger.error(f"Error calculating retention strength: {e}")
            return base_importance
    
    async def apply_forgetting_curve(self, decay_threshold: float = 0.1) -> Dict[str, int]:
        try:
            all_memories = await self.vector_store.get_all_memories()
            
            updated_count = 0
            forgotten_count = 0
            
            for i, memory_id in enumerate(all_memories.get("ids", [])):
                metadata = all_memories["metadatas"][i]
                
                # Extract memory attributes
                timestamp = metadata.get("timestamp", datetime.now().isoformat())
                last_accessed = metadata.get("last_accessed", timestamp)
                access_count = metadata.get("access_count", 0)
                current_importance = metadata.get("importance", 1.0)
                
                # Calculate new importance based on forgetting curve
                new_importance = self.calculate_retention_strength(
                    timestamp, last_accessed, access_count, current_importance
                )
                
                # If importance falls below threshold, delete the memory
                if new_importance < decay_threshold:
                    await self.vector_store.delete_memory(memory_id)
                    forgotten_count += 1
                    logger.debug(f"Forgot memory {memory_id} (importance: {new_importance:.3f})")
                else:
                    # Update the memory's importance
                    await self.vector_store.update_memory_importance(memory_id, new_importance)
                    updated_count += 1
                    logger.debug(f"Updated memory {memory_id} importance: {current_importance:.3f} -> {new_importance:.3f}")
            
            logger.info(f"Forgetting curve applied: {updated_count} updated, {forgotten_count} forgotten")
            
            return {
                "updated": updated_count,
                "forgotten": forgotten_count,
                "total_processed": updated_count + forgotten_count
            }
            
        except Exception as e:
            logger.error(f"Error applying forgetting curve: {e}")
            return {"error": str(e), "updated": 0, "forgotten": 0, "total_processed": 0}
    
    async def get_forgetting_schedule(self) -> List[Dict[str, Any]]:
        try:
            all_memories = await self.vector_store.get_all_memories()
            
            schedule = []
            for i, memory_id in enumerate(all_memories.get("ids", [])):
                metadata = all_memories["metadatas"][i]
                content = all_memories["documents"][i]
                
                timestamp = metadata.get("timestamp", datetime.now().isoformat())
                last_accessed = metadata.get("last_accessed", timestamp)
                access_count = metadata.get("access_count", 0)
                current_importance = metadata.get("importance", 1.0)
                
                # Calculate predicted importance in 1, 7, and 30 days
                current_time = datetime.now()
                
                predictions = {}
                for days in [1, 7, 30]:
                    future_time = current_time + timedelta(days=days)
                    # Simulate what importance would be at that time
                    simulated_last_access = last_accessed
                    predicted_importance = self.calculate_retention_strength(
                        timestamp, simulated_last_access, access_count, current_importance
                    )
                    # Apply additional decay for time passage
                    time_decay = math.exp(-days / 30)  # 30-day half-life
                    predicted_importance *= time_decay
                    predictions[f"day_{days}"] = round(predicted_importance, 3)
                
                schedule.append({
                    "memory_id": memory_id,
                    "content_preview": content[:100] + "..." if len(content) > 100 else content,
                    "current_importance": round(current_importance, 3),
                    "predictions": predictions,
                    "created": timestamp,
                    "last_accessed": last_accessed,
                    "access_count": access_count
                })
            
            # Sort by predicted importance (ascending - most likely to be forgotten first)
            schedule.sort(key=lambda x: x["predictions"]["day_7"])
            
            return schedule
            
        except Exception as e:
            logger.error(f"Error generating forgetting schedule: {e}")
            return []
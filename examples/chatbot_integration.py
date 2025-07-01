"""Example of integrating MemoryBank with a chatbot."""

import asyncio
from typing import List, Dict, Any
from memorybank import AsyncMemoryBankClient, MemoryBankConfig, MemoryMetadata, ChatResponse

class MemoryAwareChatbot:
    """A chatbot that uses MemoryBank for long-term memory."""
    
    def __init__(self, config: MemoryBankConfig):
        self.config = config
        self.client = AsyncMemoryBankClient(config)
        self.conversation_history: List[Dict[str, str]] = []
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def chat(
        self, 
        user_message: str, 
        user_id: str, 
        session_id: str = None
    ) -> ChatResponse:
        """Process a chat message with memory integration."""
        
        # Create metadata for this conversation
        metadata = MemoryMetadata(
            user_id=user_id,
            session_id=session_id,
            category="conversation"
        )
        
        # Store the user's message as a memory
        await self.client.store_memory(
            f"User said: {user_message}",
            metadata=MemoryMetadata(
                user_id=user_id,
                session_id=session_id,
                category="user_message",
                tags=["conversation"]
            )
        )
        
        # Get chat response with memory augmentation
        system_prompt = (
            "You are a helpful AI assistant with long-term memory. "
            "Use the provided memories to give personalized responses. "
            "Reference past conversations when relevant."
        )
        
        response = await self.client.chat(
            user_message,
            system_prompt=system_prompt,
            metadata=metadata
        )
        
        # Store the assistant's response as a memory
        await self.client.store_memory(
            f"Assistant responded: {response.response}",
            metadata=MemoryMetadata(
                user_id=user_id,
                session_id=session_id,
                category="assistant_message",
                tags=["conversation"]
            )
        )
        
        # Add to conversation history
        self.conversation_history.append({
            "user": user_message,
            "assistant": response.response,
            "memories_used": len(response.memories_used)
        })
        
        return response
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of what we know about a user."""
        
        # Retrieve all memories for this user
        memories = await self.client.retrieve_memories(
            "Tell me everything about this user",
            top_k=20,
            metadata_filter=MemoryMetadata(user_id=user_id)
        )
        
        # Categorize memories
        profile = {
            "user_id": user_id,
            "total_memories": len(memories),
            "preferences": [],
            "habits": [],
            "projects": [],
            "conversations": [],
            "other": []
        }
        
        for result in memories:
            memory = result.memory
            category = memory.metadata.category or "other"
            
            if category in profile:
                profile[category].append({
                    "content": memory.content,
                    "importance": memory.importance,
                    "last_accessed": memory.last_accessed
                })
            else:
                profile["other"].append({
                    "content": memory.content,
                    "category": category,
                    "importance": memory.importance
                })
        
        return profile
    
    async def forget_user_data(self, user_id: str) -> int:
        """Delete all memories for a specific user (GDPR compliance)."""
        
        # Get all memories for the user
        memories = await self.client.retrieve_memories(
            "all memories",  # Broad query to get all memories
            top_k=1000,  # Large number to get all
            metadata_filter=MemoryMetadata(user_id=user_id)
        )
        
        # Delete each memory
        deleted_count = 0
        for result in memories:
            success = await self.client.forget_memory(result.memory.memory_id)
            if success:
                deleted_count += 1
        
        return deleted_count

async def chatbot_demo():
    """Demonstrate the memory-aware chatbot."""
    print("=== Memory-Aware Chatbot Demo ===")
    
    config = MemoryBankConfig.from_env()
    
    async with MemoryAwareChatbot(config) as bot:
        user_id = "demo_user_123"
        session_id = "session_001"
        
        # Simulate a conversation
        conversations = [
            "Hi, I'm John and I love hiking and photography",
            "I'm working on a Python machine learning project",
            "My favorite food is Italian cuisine, especially pasta",
            "I work as a software engineer at a tech company",
            "I'm planning a trip to Italy next month"
        ]
        
        print("Starting conversation...")
        for i, message in enumerate(conversations, 1):
            print(f"\nUser: {message}")
            
            response = await bot.chat(message, user_id, session_id)
            print(f"Bot: {response.response}")
            print(f"Memories used: {len(response.memories_used)}")
            
            # Show which memories were used
            if response.memories_used:
                print("Relevant memories:")
                for result in response.memories_used[:2]:  # Show top 2
                    print(f"  - {result.memory.content} (score: {result.score:.3f})")
        
        # Ask follow-up questions that should use memory
        follow_ups = [
            "What do you remember about my hobbies?",
            "What programming project am I working on?",
            "What's my job?",
            "Where am I planning to travel?"
        ]
        
        print("\n" + "="*50)
        print("Follow-up questions (testing memory)...")
        
        for question in follow_ups:
            print(f"\nUser: {question}")
            response = await bot.chat(question, user_id, session_id)
            print(f"Bot: {response.response}")
        
        # Show user profile
        print("\n" + "="*50)
        print("User Profile Summary:")
        profile = await bot.get_user_profile(user_id)
        
        print(f"Total memories: {profile['total_memories']}")
        for category, items in profile.items():
            if category != "total_memories" and items:
                print(f"\n{category.title()}:")
                for item in items[:3]:  # Show top 3 per category
                    print(f"  - {item['content']}")

if __name__ == "__main__":
    asyncio.run(chatbot_demo())
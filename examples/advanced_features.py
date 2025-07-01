"""Advanced features and use cases for MemoryBank SDK."""

import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
from memorybank import AsyncMemoryBankClient, MemoryBankConfig, MemoryMetadata

async def memory_analytics_example():
    """Demonstrate memory analytics and insights."""
    print("=== Memory Analytics Example ===")
    
    config = MemoryBankConfig.from_env()
    
    async with AsyncMemoryBankClient(config) as client:
        # Store diverse memories for analysis
        sample_memories = [
            ("User prefers React over Vue for frontend development", {"category": "preference", "tags": ["frontend", "react"]}),
            ("User had a great experience with the new restaurant downtown", {"category": "experience", "tags": ["food", "restaurant"]}),
            ("User is learning Spanish and practices 30 minutes daily", {"category": "learning", "tags": ["language", "spanish"]}),
            ("User mentioned having trouble with async programming", {"category": "problem", "tags": ["programming", "async"]}),
            ("User successfully deployed their app to production", {"category": "achievement", "tags": ["deployment", "success"]}),
            ("User prefers working in the morning hours", {"category": "preference", "tags": ["schedule", "morning"]}),
            ("User is interested in machine learning and AI", {"category": "interest", "tags": ["ml", "ai"]}),
        ]
        
        user_id = "analytics_user"
        
        print("Storing sample memories...")
        for content, metadata in sample_memories:
            metadata["user_id"] = user_id
            await client.store_memory(content, MemoryMetadata.from_dict(metadata))
        
        # Analyze memory patterns
        print("\nAnalyzing memory patterns...")
        
        # Get memories by category
        categories = ["preference", "experience", "learning", "problem", "achievement"]
        
        for category in categories:
            memories = await client.retrieve_memories(
                f"{category} related memories",
                top_k=10,
                metadata_filter=MemoryMetadata(user_id=user_id, category=category)
            )
            print(f"{category.title()}: {len(memories)} memories")
        
        # Get overall statistics
        stats = await client.get_memory_stats()
        print(f"\nOverall Statistics:")
        print(f"Total memories: {stats.total_memories}")
        print(f"Average importance: {stats.avg_importance:.3f}")
        print(f"Oldest memory: {stats.oldest_memory}")
        print(f"Newest memory: {stats.newest_memory}")

async def multi_user_example():
    """Demonstrate multi-user memory isolation."""
    print("\n=== Multi-User Memory Isolation ===")
    
    config = MemoryBankConfig.from_env()
    
    async with AsyncMemoryBankClient(config) as client:
        # Create memories for different users
        users_data = {
            "alice": [
                "Alice loves Python programming",
                "Alice works at a startup",
                "Alice enjoys rock climbing"
            ],
            "bob": [
                "Bob prefers Java development",
                "Bob works at a large corporation", 
                "Bob likes playing chess"
            ],
            "charlie": [
                "Charlie is a data scientist",
                "Charlie uses R and Python",
                "Charlie loves hiking"
            ]
        }
        
        # Store memories for each user
        print("Storing memories for multiple users...")
        for user_id, memories in users_data.items():
            for memory in memories:
                await client.store_memory(
                    memory,
                    MemoryMetadata(user_id=user_id, category="profile")
                )
        
        # Test memory isolation
        print("\nTesting memory isolation...")
        for user_id in users_data.keys():
            memories = await client.retrieve_memories(
                "Tell me about this user",
                top_k=5,
                metadata_filter=MemoryMetadata(user_id=user_id)
            )
            
            print(f"\n{user_id.title()}'s memories:")
            for result in memories:
                print(f"  - {result.memory.content} (score: {result.score:.3f})")

async def forgetting_curve_example():
    """Demonstrate forgetting curve functionality."""
    print("\n=== Forgetting Curve Example ===")
    
    config = MemoryBankConfig.from_env()
    
    async with AsyncMemoryBankClient(config) as client:
        user_id = "forgetting_user"
        
        # Store some memories
        print("Storing memories with different importance levels...")
        
        important_memory = await client.store_memory(
            "This is very important information that should be remembered",
            MemoryMetadata(user_id=user_id, category="important")
        )
        
        casual_memory = await client.store_memory(
            "This is casual information that can be forgotten",
            MemoryMetadata(user_id=user_id, category="casual")
        )
        
        # Check initial state
        stats_before = await client.get_memory_stats()
        print(f"Memories before forgetting curve: {stats_before.total_memories}")
        
        # Run forgetting curve
        print("Running forgetting curve...")
        result = await client.run_forgetting_curve()
        print(f"Forgetting curve result: {result}")
        
        # Check state after
        stats_after = await client.get_memory_stats()
        print(f"Memories after forgetting curve: {stats_after.total_memories}")

async def batch_operations_example():
    """Demonstrate efficient batch operations."""
    print("\n=== Batch Operations Example ===")
    
    config = MemoryBankConfig.from_env()
    
    async with AsyncMemoryBankClient(config) as client:
        user_id = "batch_user"
        
        # Batch store memories
        print("Batch storing memories...")
        memories_to_store = [
            ("User likes coffee", {"category": "preference"}),
            ("User is learning guitar", {"category": "hobby"}),
            ("User works in marketing", {"category": "job"}),
            ("User has a cat named Whiskers", {"category": "personal"}),
            ("User lives in San Francisco", {"category": "location"}),
        ]
        
        # Store all memories concurrently
        store_tasks = []
        for content, metadata in memories_to_store:
            metadata["user_id"] = user_id
            task = client.store_memory(content, MemoryMetadata.from_dict(metadata))
            store_tasks.append(task)
        
        memory_ids = await asyncio.gather(*store_tasks)
        print(f"Stored {len(memory_ids)} memories concurrently")
        
        # Batch retrieve with different queries
        print("Batch retrieving memories...")
        queries = [
            "What does the user like to drink?",
            "What hobbies does the user have?",
            "Where does the user work?",
            "Tell me about the user's pets",
            "Where does the user live?"
        ]
        
        retrieve_tasks = []
        for query in queries:
            task = client.retrieve_memories(
                query,
                top_k=3,
                metadata_filter=MemoryMetadata(user_id=user_id)
            )
            retrieve_tasks.append(task)
        
        results = await asyncio.gather(*retrieve_tasks)
        
        for i, (query, memories) in enumerate(zip(queries, results)):
            print(f"\nQuery {i+1}: {query}")
            for result in memories[:1]:  # Show top result
                print(f"  Answer: {result.memory.content} (score: {result.score:.3f})")

async def error_handling_example():
    """Demonstrate error handling and resilience."""
    print("\n=== Error Handling Example ===")
    
    # Test with invalid configuration
    invalid_config = MemoryBankConfig(
        api_key="invalid-key",
        base_url="http://localhost:9999",  # Wrong port
        timeout=5,
        max_retries=1
    )
    
    try:
        async with AsyncMemoryBankClient(invalid_config) as client:
            await client.health_check()
    except Exception as e:
        print(f"Expected error with invalid config: {type(e).__name__}: {e}")
    
    # Test with valid config but invalid operations
    config = MemoryBankConfig.from_env()
    
    async with AsyncMemoryBankClient(config) as client:
        # Try to forget non-existent memory
        try:
            result = await client.forget_memory("non-existent-id")
            print(f"Forgetting non-existent memory: {result}")
        except Exception as e:
            print(f"Error forgetting non-existent memory: {e}")
        
        # Try with empty query
        try:
            memories = await client.retrieve_memories("", top_k=1)
            print(f"Empty query returned {len(memories)} memories")
        except Exception as e:
            print(f"Error with empty query: {e}")

async def main():
    """Run all advanced examples."""
    try:
        await memory_analytics_example()
        await multi_user_example()
        await forgetting_curve_example()
        await batch_operations_example()
        await error_handling_example()
        
        print("\n=== All examples completed successfully! ===")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure the MemoryBank server is running and properly configured")

if __name__ == "__main__":
    asyncio.run(main())
"""Basic usage examples for MemoryBank SDK."""

import asyncio
from memorybank import MemoryBankClient, AsyncMemoryBankClient, MemoryBankConfig, MemoryMetadata

def sync_example():
    """Example using synchronous client."""
    print("=== Synchronous MemoryBank Example ===")
    
    # Configure the client
    config = MemoryBankConfig(
        api_key="your-api-key-here",
        base_url="http://localhost:8000",
        llm_provider="claude"
    )
    
    # Create client
    with MemoryBankClient(config) as client:
        # Store some memories
        print("Storing memories...")
        
        memory_id1 = client.store_memory(
            "User prefers dark mode for all applications",
            metadata=MemoryMetadata(user_id="user123", category="preference")
        )
        print(f"Stored memory: {memory_id1}")
        
        memory_id2 = client.store_memory(
            "User is working on a Python project using FastAPI",
            metadata=MemoryMetadata(user_id="user123", category="project", tags=["python", "fastapi"])
        )
        print(f"Stored memory: {memory_id2}")
        
        # Retrieve memories
        print("\nRetrieving memories...")
        memories = client.retrieve_memories(
            "What does the user prefer for UI?",
            top_k=5,
            metadata_filter=MemoryMetadata(user_id="user123")
        )
        
        for result in memories:
            print(f"Score: {result.score:.3f} - {result.memory.content}")
        
        # Chat with memory
        print("\nChatting with memory...")
        response = client.chat(
            "Help me set up my development environment",
            system_prompt="You are a helpful coding assistant",
            metadata=MemoryMetadata(user_id="user123")
        )
        
        print(f"Response: {response.response}")
        print(f"Memories used: {len(response.memories_used)}")
        
        # Get statistics
        print("\nMemory statistics...")
        stats = client.get_memory_stats()
        print(f"Total memories: {stats.total_memories}")
        print(f"Average importance: {stats.avg_importance}")

async def async_example():
    """Example using asynchronous client."""
    print("\n=== Asynchronous MemoryBank Example ===")
    
    # Configure from environment variables
    config = MemoryBankConfig.from_env()
    
    # Create async client
    async with AsyncMemoryBankClient(config) as client:
        # Store multiple memories concurrently
        print("Storing memories concurrently...")
        
        tasks = [
            client.store_memory(
                "User loves coffee and drinks it every morning",
                metadata=MemoryMetadata(user_id="user456", category="habit")
            ),
            client.store_memory(
                "User is learning machine learning and AI",
                metadata=MemoryMetadata(user_id="user456", category="learning", tags=["ml", "ai"])
            ),
            client.store_memory(
                "User works remotely from home office",
                metadata=MemoryMetadata(user_id="user456", category="work")
            )
        ]
        
        memory_ids = await asyncio.gather(*tasks)
        print(f"Stored {len(memory_ids)} memories")
        
        # Query memories
        print("\nQuerying memories...")
        memories = await client.retrieve_memories(
            "Tell me about the user's habits and work",
            top_k=3,
            metadata_filter=MemoryMetadata(user_id="user456")
        )
        
        for result in memories:
            print(f"Score: {result.score:.3f} - {result.memory.content}")
        
        # Multiple chat interactions
        print("\nMultiple chat interactions...")
        chat_tasks = [
            client.chat("What should I drink this morning?", metadata=MemoryMetadata(user_id="user456")),
            client.chat("What am I learning about?", metadata=MemoryMetadata(user_id="user456")),
            client.chat("Where do I work?", metadata=MemoryMetadata(user_id="user456"))
        ]
        
        responses = await asyncio.gather(*chat_tasks)
        for i, response in enumerate(responses, 1):
            print(f"Chat {i}: {response.response}")

def configuration_example():
    """Example of different configuration methods."""
    print("\n=== Configuration Examples ===")
    
    # Method 1: Direct configuration
    config1 = MemoryBankConfig(
        api_key="your-api-key",
        base_url="https://your-server.com",
        llm_provider="openai",
        openai_api_key="your-openai-key",
        default_top_k=10
    )
    
    # Method 2: From environment variables
    config2 = MemoryBankConfig.from_env()
    
    # Method 3: From JSON file
    config3 = MemoryBankConfig(
        api_key="test-key",
        llm_provider="claude",
        anthropic_api_key="claude-key"
    )
    config3.to_file("config.json")  # Save to file
    config3_loaded = MemoryBankConfig.from_file("config.json")  # Load from file
    
    print("Configuration methods demonstrated")

if __name__ == "__main__":
    try:
        # Run sync example
        sync_example()
        
        # Run async example
        asyncio.run(async_example())
        
        # Run configuration example
        configuration_example()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the MemoryBank server is running and API keys are configured")
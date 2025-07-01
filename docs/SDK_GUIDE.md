# MemoryBank SDK Guide

This guide covers how to use the MemoryBank Python SDK to integrate long-term memory capabilities into your applications.

## Installation

```bash
pip install memorybank
```

## Basic Usage

### Configuration

The SDK can be configured in several ways:

#### Method 1: Direct Configuration
```python
from memorybank import MemoryBankConfig

config = MemoryBankConfig(
    api_key="your-api-key",
    base_url="http://localhost:8000",
    llm_provider="claude",
    anthropic_api_key="your-claude-key"
)
```

#### Method 2: Environment Variables
```bash
export MEMORYBANK_API_KEY="your-api-key"
export MEMORYBANK_BASE_URL="http://localhost:8000"
export MEMORYBANK_LLM_PROVIDER="claude"
export ANTHROPIC_API_KEY="your-claude-key"
```

```python
from memorybank import MemoryBankConfig

config = MemoryBankConfig.from_env()
```

#### Method 3: Configuration File
```python
from memorybank import MemoryBankConfig

# Save configuration
config = MemoryBankConfig(api_key="your-key", llm_provider="claude")
config.to_file("memorybank-config.json")

# Load configuration
config = MemoryBankConfig.from_file("memorybank-config.json")
```

### Basic Operations

#### Synchronous Client
```python
from memorybank import MemoryBankClient, MemoryMetadata

with MemoryBankClient(config) as client:
    # Store a memory
    memory_id = client.store_memory(
        "User prefers dark mode",
        metadata=MemoryMetadata(user_id="user123", category="preference")
    )
    
    # Retrieve memories
    memories = client.retrieve_memories("What does the user prefer?")
    for result in memories:
        print(f"Score: {result.score} - {result.memory.content}")
    
    # Chat with memory
    response = client.chat("What should I use for my UI theme?")
    print(response.response)
```

#### Asynchronous Client
```python
import asyncio
from memorybank import AsyncMemoryBankClient, MemoryMetadata

async def main():
    async with AsyncMemoryBankClient(config) as client:
        # Store multiple memories concurrently
        tasks = [
            client.store_memory("User likes coffee", MemoryMetadata(user_id="user123")),
            client.store_memory("User uses Python", MemoryMetadata(user_id="user123")),
            client.store_memory("User works remotely", MemoryMetadata(user_id="user123"))
        ]
        memory_ids = await asyncio.gather(*tasks)
        
        # Retrieve memories
        memories = await client.retrieve_memories("Tell me about the user")
        
        # Chat
        response = await client.chat("What do you know about me?")
        print(response.response)

asyncio.run(main())
```

## Advanced Features

### Memory Metadata

Use metadata to organize and filter memories:

```python
from memorybank import MemoryMetadata

# Rich metadata
metadata = MemoryMetadata(
    user_id="user123",
    session_id="session456", 
    category="preference",
    tags=["ui", "theme", "accessibility"],
    custom_fields={"importance": "high", "source": "user_input"}
)

# Store with metadata
memory_id = client.store_memory("User prefers high contrast mode", metadata)

# Filter by metadata
memories = client.retrieve_memories(
    "accessibility preferences",
    metadata_filter=MemoryMetadata(user_id="user123", category="preference")
)
```

### Multi-User Support

Keep memories separate for different users:

```python
# Store memories for different users
alice_metadata = MemoryMetadata(user_id="alice", category="hobby")
bob_metadata = MemoryMetadata(user_id="bob", category="hobby")

client.store_memory("Alice loves painting", alice_metadata)
client.store_memory("Bob enjoys photography", bob_metadata)

# Retrieve only Alice's memories
alice_memories = client.retrieve_memories(
    "hobbies",
    metadata_filter=MemoryMetadata(user_id="alice")
)
```

### Memory Analytics

```python
# Get memory statistics
stats = client.get_memory_stats()
print(f"Total memories: {stats.total_memories}")
print(f"Average importance: {stats.avg_importance}")
print(f"Oldest memory: {stats.oldest_memory}")

# Manual forgetting curve
result = client.run_forgetting_curve()
print(f"Forgetting curve applied at: {result['timestamp']}")
```

### Chat with Context

```python
# Chat with specific context
response = client.chat(
    "Help me with my Python project",
    system_prompt="You are a helpful coding assistant",
    metadata=MemoryMetadata(user_id="developer123")
)

print(f"Response: {response.response}")
print(f"Model used: {response.model_used}")
print(f"Memories used: {len(response.memories_used)}")

# Show which memories were referenced
for result in response.memories_used:
    print(f"- {result.memory.content} (score: {result.score})")
```

## Integration Patterns

### Chatbot Integration

```python
class MemoryAwareChatbot:
    def __init__(self, config):
        self.client = AsyncMemoryBankClient(config)
    
    async def process_message(self, user_message, user_id):
        # Store user message
        await self.client.store_memory(
            f"User said: {user_message}",
            MemoryMetadata(user_id=user_id, category="conversation")
        )
        
        # Get response with memory
        response = await self.client.chat(
            user_message,
            metadata=MemoryMetadata(user_id=user_id)
        )
        
        # Store assistant response
        await self.client.store_memory(
            f"Assistant responded: {response.response}",
            MemoryMetadata(user_id=user_id, category="conversation")
        )
        
        return response
```

### Learning System

```python
class LearningAssistant:
    def __init__(self, config):
        self.client = MemoryBankClient(config)
    
    def learn_user_preference(self, user_id, preference):
        """Learn and store a user preference."""
        self.client.store_memory(
            preference,
            MemoryMetadata(
                user_id=user_id,
                category="preference",
                tags=["learned", "user_input"]
            )
        )
    
    def get_personalized_recommendations(self, user_id, topic):
        """Get recommendations based on learned preferences."""
        # Retrieve relevant preferences
        preferences = self.client.retrieve_memories(
            f"preferences about {topic}",
            metadata_filter=MemoryMetadata(user_id=user_id, category="preference")
        )
        
        # Generate personalized response
        context = "\n".join([p.memory.content for p in preferences])
        response = self.client.chat(
            f"Based on my preferences, recommend {topic} options",
            system_prompt=f"User preferences: {context}",
            metadata=MemoryMetadata(user_id=user_id)
        )
        
        return response.response
```

## Error Handling

```python
from memorybank import MemoryBankError, AuthenticationError, APIError

try:
    with MemoryBankClient(config) as client:
        memory_id = client.store_memory("Test memory")
        memories = client.retrieve_memories("test query")
        
except AuthenticationError:
    print("Invalid API key or authentication failed")
except APIError as e:
    print(f"API error (status {e.status_code}): {e}")
except MemoryBankError as e:
    print(f"MemoryBank error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Best Practices

### Batch Operations
```python
import asyncio

async def batch_store_memories(client, memories_data):
    """Store multiple memories concurrently."""
    tasks = []
    for content, metadata in memories_data:
        task = client.store_memory(content, metadata)
        tasks.append(task)
    
    return await asyncio.gather(*tasks)

async def batch_retrieve_memories(client, queries, user_id):
    """Retrieve memories for multiple queries concurrently."""
    tasks = []
    for query in queries:
        task = client.retrieve_memories(
            query,
            metadata_filter=MemoryMetadata(user_id=user_id)
        )
        tasks.append(task)
    
    return await asyncio.gather(*tasks)
```

### Connection Pooling
```python
# Use async context manager for connection reuse
async with AsyncMemoryBankClient(config) as client:
    # Multiple operations reuse the same connection
    await client.store_memory("Memory 1")
    await client.store_memory("Memory 2")
    await client.retrieve_memories("Query 1")
    await client.retrieve_memories("Query 2")
```

### Configuration Optimization
```python
# Optimize for your use case
config = MemoryBankConfig(
    api_key="your-key",
    timeout=60,  # Longer timeout for slow networks
    max_retries=5,  # More retries for reliability
    retry_delay=2.0,  # Longer delay between retries
    default_top_k=10  # Retrieve more memories by default
)
```

## CLI Usage

The SDK includes a command-line interface:

```bash
# Configure
memorybank configure

# Store memories
memorybank store "User prefers Python" --user-id user123 --category language

# Retrieve memories
memorybank retrieve "programming languages" --user-id user123 --format table

# Chat
memorybank chat "What should I learn next?" --user-id user123

# Statistics
memorybank stats

# Health check
memorybank health
```

For more CLI options:
```bash
memorybank --help
memorybank store --help
memorybank retrieve --help
```

## Configuration Reference

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `api_key` | `MEMORYBANK_API_KEY` | None | API key for authentication |
| `base_url` | `MEMORYBANK_BASE_URL` | `http://localhost:8000` | Server base URL |
| `timeout` | `MEMORYBANK_TIMEOUT` | 30 | Request timeout (seconds) |
| `llm_provider` | `MEMORYBANK_LLM_PROVIDER` | `claude` | LLM provider (claude/openai/gemini) |
| `embedding_provider` | `MEMORYBANK_EMBEDDING_PROVIDER` | `openai` | Embedding provider |
| `default_top_k` | `MEMORYBANK_DEFAULT_TOP_K` | 5 | Default number of memories to retrieve |
| `max_retries` | `MEMORYBANK_MAX_RETRIES` | 3 | Maximum retry attempts |
| `retry_delay` | `MEMORYBANK_RETRY_DELAY` | 1.0 | Delay between retries (seconds) |

## Next Steps

- Check out the [examples](../examples/) directory for complete usage examples
- See the [API documentation](API.md) for detailed endpoint information  
- Visit the [server setup guide](SERVER_SETUP.md) for running your own instance
- Read about [memory optimization](OPTIMIZATION.md) for production deployments
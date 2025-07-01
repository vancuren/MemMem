# MemoryBank API - Long-Term Memory System

A MemoryBank-inspired external long-term memory system for conversational AI agents, built with FastAPI and featuring intelligent retrieval, automatic forgetting, and multi-LLM support.

## Features

- 🧠 **Persistent Memory Storage** - Store and retrieve memories using vector embeddings
- 🔍 **Intelligent Retrieval** - Semantic search for relevant memories
- ⏰ **Automatic Forgetting** - Ebbinghaus curve-based memory decay
- 🤖 **Multi-LLM Support** - Works with Claude, OpenAI GPT-4, and Google Gemini
- 📊 **Memory Analytics** - Track memory statistics and importance
- 🔄 **Scheduled Maintenance** - Automatic memory cleanup and optimization

## Quick Start

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Set Up Environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Run the Server**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Core Memory Operations

#### Store Memory
```bash
curl -X POST "http://localhost:8000/store_memory" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers dark mode for all applications",
    "metadata": {"user_id": "user123", "category": "preference"}
  }'
```

#### Retrieve Memory
```bash
curl -X POST "http://localhost:8000/retrieve_memory" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What does the user prefer for UI?",
    "top_k": 3,
    "metadata": {"user_id": "user123"}
  }'
```

#### Forget Memory
```bash
curl -X POST "http://localhost:8000/forget_memory" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_id": "abc123-uuid"
  }'
```

### Chat with Memory
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Help me set up my development environment",
    "system_prompt": "You are a helpful coding assistant"
  }'
```

### Memory Management

#### Get Memory Statistics
```bash
curl -X GET "http://localhost:8000/memory_stats" \
  -H "Authorization: Bearer your_api_key"
```

#### Run Forgetting Curve Manually
```bash
curl -X POST "http://localhost:8000/run_forgetting_curve" \
  -H "Authorization: Bearer your_api_key"
```

#### Check Scheduler Status
```bash
curl -X GET "http://localhost:8000/scheduler_status" \
  -H "Authorization: Bearer your_api_key"
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key for embeddings and GPT models |
| `ANTHROPIC_API_KEY` | - | Anthropic API key for Claude models |
| `GOOGLE_API_KEY` | - | Google API key for Gemini models |
| `LLM_PROVIDER` | `claude` | Default LLM provider (claude/openai/gemini) |
| `EMBEDDING_PROVIDER` | `openai` | Embedding provider (openai/huggingface) |
| `CHROMA_DB_PATH` | `./memory_db` | Path for Chroma vector database |
| `API_KEY` | - | API key for securing the memory service |
| `FORGETTING_INTERVAL_HOURS` | `24` | Hours between forgetting curve applications |
| `MAINTENANCE_INTERVAL_HOURS` | `168` | Hours between full memory maintenance |
| `FORGETTING_THRESHOLD` | `0.1` | Importance threshold below which memories are forgotten |

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐
│   LLM Client    │───▶│  MemoryBank API │───▶│  Chroma Vector DB   │
│ (Claude/GPT/    │    │                 │    │                     │
│  Gemini)        │    │  - Store        │    │  - Embeddings       │
└─────────────────┘    │  - Retrieve     │    │  - Metadata         │
                       │  - Forget       │    │  - Similarity       │
┌─────────────────┐    │  - Chat         │    │    Search           │
│   Scheduler     │───▶│                 │    └─────────────────────┘
│                 │    └─────────────────┘              │
│ - Forgetting    │              │                      │
│   Curve         │              ▼                      │
│ - Maintenance   │    ┌─────────────────┐              │
└─────────────────┘    │  OpenAI         │              │
                       │  Embeddings     │◀─────────────┘
                       └─────────────────┘
```

## Memory Schema

Each memory contains:
- `memory_id`: Unique identifier
- `content`: The actual memory text
- `embedding`: Vector representation
- `timestamp`: Creation time
- `last_accessed`: Last retrieval time
- `importance`: Dynamic importance score (0.0-2.0)
- `access_count`: Number of times accessed
- `metadata`: Custom metadata (user_id, tags, etc.)

## Forgetting Mechanism

The system implements an Ebbinghaus curve-inspired forgetting mechanism:

1. **Retention Calculation**: `R(t) = e^(-t/S)` where:
   - `R(t)` is retention at time t
   - `t` is time since last access
   - `S` is strength factor (increased by access frequency)

2. **Importance Decay**: Memories lose importance over time
3. **Access Boost**: Frequently accessed memories gain importance
4. **Automatic Cleanup**: Memories below threshold are automatically deleted

## Development

### Project Structure
```
MemMem/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── src/
│   ├── __init__.py
│   ├── models.py          # Pydantic models
│   ├── memory_manager.py  # Core memory operations
│   ├── vector_store.py    # Chroma DB integration
│   ├── embedding_client.py # Embedding providers
│   ├── llm_client.py      # LLM providers
│   ├── forgetting_curve.py # Memory decay logic
│   └── scheduler.py       # Background tasks
└── memory_db/             # Chroma database (auto-created)
```

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when implemented)
pytest tests/
```

## License

MIT License - see LICENSE file for details.
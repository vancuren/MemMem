# 📑 Technical Project Requirements

## External Long-Term Memory System (MemoryBank-inspired)

# Claude MemoryBank Prototype – Long-Term Memory System

This document defines the technical requirements and system behavior for a MemoryBank-inspired long-term memory module that integrates with Claude via its API. The system allows persistent storage, intelligent retrieval, and aging/forgetting of user memories across sessions. It is designed to be compatible with **all major LLM APIs** by using modular abstractions and configuration-based routing.


---

## 📌 **1. Project Overview**

Build an external long-term memory system for a conversational AI agent using Anthropic’s Claude API. This system should store, retrieve, and manage long-term memories to allow the agent to recall relevant information dynamically during user interactions. It should closely resemble the **MemoryBank** system as described in the AAAI 2024 paper, implementing key features like efficient retrieval, evolving storage, and a human-like forgetting mechanism.

---

## 📌 **2. Objectives & Deliverables**

* A **Python FastAPI** service with endpoints for memory operations (`store`, `retrieve`, `forget`).
* Integration with Anthropic Claude API, OpenAI's SDk or Google Gemini's API to use retrieved memories in context-aware responses.
* Persistent external storage for long-term memory using vector embeddings (**Chroma Vector DB**).
* Autonomous memory management with periodic "forgetting" based on memory importance.
* Detailed inline documentation and clear modular code structure.
* Add persistent memory to Claude-based and other model-based agents
* Enable retrieval of relevant past interactions for better personalization
* Implement memory decay over time using an Ebbinghaus-style forgetting curve
* Use non-parametric memory (external DB + embeddings) to avoid retraining
* Ensure compatibility with Claude, OpenAI GPT-4, Gemini, Mistral, LLaMA, etc.

---

## 📌 **3. Tech Stack & Tools**

| Component         | Technology / Library                         |
| ----------------- | -------------------------------------------- |
| API Framework     | Python FastAPI                               |
| Vector DB         | Chroma (local, easy-to-deploy)               |
| Embedding Service | OpenAI Embeddings (`text-embedding-ada-002`) |
| LLM Integration   | Anthropic Claude API, Openai 4o API, Google Gemini API |
| Scheduling Jobs   | Python Cron or APScheduler                   |
| Security          | Basic API keys/token authentication          |
| Logging           | Python’s built-in logging                    |

---

## 📌 **4. System Architecture (Detailed)**

```plaintext
LLM User Interaction
    │
    └──→ FastAPI Memory API Service
            │
            ├─── Memory Management Controller
            │       ├── store_memory(content, metadata)
            │       ├── retrieve_memory(query, metadata, top_k)
            │       └── forget_memory(memory_id)
            │
            ├─── Embedding Generator (OpenAI, HuggingFace API, or Internal)
            └─── Chroma Vector Database (Persistent Memory Storage)
                    │
                    └── Scheduled Forgetting Job
                            └── Periodically decays memory importance and deletes low-value memories
```

---

## 📌 **5. Detailed Data Schema**

Each memory entry in Chroma DB:

| Field           | Type          | Description                                   |
| --------------- | ------------- | --------------------------------------------- |
| `memory_id`     | String (UUID) | Unique memory identifier                      |
| `content`       | Text          | Original interaction or summarized memory     |
| `embedding`     | Vector (list) | Embedding of the memory                       |
| `timestamp`     | DateTime      | When memory was created                       |
| `last_accessed` | DateTime      | Last time memory was retrieved                |
| `importance`    | Float         | Score adjusted by retrieval frequency & decay |
| `metadata`      | JSON          | Contextual tags (user\_id, category, source)  |


## 🧠 Memory Object Schema

```json
{
  "memory_id": "uuid",
  "content": "User likes oat milk lattes",
  "embedding": [float, ...],
  "timestamp": "ISO 8601 datetime",
  "last_accessed": "ISO 8601 datetime",
  "importance": 1.0,
  "metadata": {
    "user_id": "u123",
    "tags": ["preference"]
  }
}
```


## 📌 **6. API Endpoint Specifications**

### ✅ **Store Memory (`POST /store_memory`)**

Stores a memory from an interaction or summary.

* **Request** (`application/json`):

```json
{
  "content": "User's favorite color is blue.",
  "metadata": {
    "user_id": "user123"
  }
}
```

* **Response**:

```json
{
  "memory_id": "abc123-uuid",
  "status": "stored"
}
```

---

### ✅ **Retrieve Memory (`POST /retrieve_memory`)**

Retrieves top-k relevant memories based on a query.

* **Request** (`application/json`):

```json
{
  "query": "What's the user's favorite color?",
  "top_k": 2,
  "metadata": {
    "user_id": "user123"
  }
}
```

* **Response**:

```json
{
  "memories": [
    {
      "memory_id": "abc123-uuid",
      "content": "User's favorite color is blue.",
      "timestamp": "2024-06-30T15:00:00",
      "score": 0.93
    }
  ]
}
```

---

### ✅ **Forget Memory (`POST /forget_memory`)**

Deletes a memory entry explicitly.

* **Request** (`application/json`):

```json
{
  "memory_id": "abc123-uuid"
}
```

* **Response**:

```json
{
  "status": "deleted",
  "memory_id": "abc123-uuid"
}
```

---

## 📌 **7. Implementation Guidelines**

### 🔖 Embedding and Storage


Use OpenAI embeddings for efficiency and accuracy:

- Use `text-embedding-ada-002` or a pluggable embedding provider.
- Use a vector DB (e.g. Chroma) to store vectors and metadata.
- Update `last_accessed` and `importance` on retrieval.


```python
import openai

def generate_embedding(text):
    embedding = openai.Embedding.create(
        input=text,
        model="text-embedding-ada-002"
    )["data"][0]["embedding"]
    return embedding
```

---

### 🔑 **Vector DB (Chroma) Integration**

Sample Memory Storage and Retrieval:

```python
import chromadb
import uuid
from datetime import datetime

client = chromadb.PersistentClient(path="./memory_db")
collection = client.get_or_create_collection(name="long_term_memories")

# Storing Memory
def store_memory(content, metadata={}):
    memory_id = str(uuid.uuid4())
    embedding = generate_embedding(content)
    collection.add(
        documents=[content],
        embeddings=[embedding],
        ids=[memory_id],
        metadatas=[{
            "timestamp": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "importance": 1.0,
            **metadata
        }]
    )
    return memory_id

# Retrieving Memory
def retrieve_memory(query, top_k=3):
    query_embedding = generate_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    memories = results['documents'][0]

    # Update last_accessed & importance
    for memory_id in results['ids'][0]:
        collection.update(
            ids=[memory_id],
            metadatas=[{
                "last_accessed": datetime.now().isoformat(),
                "importance": 1.0  # Update logic as needed
            }]
        )
    return memories
```

---

### 🔑 **Memory Forgetting Mechanism**

Implement periodic forgetting inspired by the Ebbinghaus curve:

```python
def forget_low_importance(decay_rate=0.9, threshold=0.2):
    all_memories = collection.get()
    for idx, meta in enumerate(all_memories['metadatas']):
        new_importance = meta['importance'] * decay_rate
        memory_id = all_memories['ids'][idx]

        if new_importance < threshold:
            collection.delete(ids=[memory_id])
        else:
            collection.update(
                ids=[memory_id],
                metadatas=[{**meta, "importance": new_importance}]
            )
```

* Run this as a scheduled task (daily/weekly via Cron/APScheduler).

---

## 📌 **8. Claude API Integration**

Augment Claude prompts dynamically with retrieved memories:

```python
import anthropic

client = anthropic.Anthropic(api_key="your-claude-api-key")

def claude_response(user_query, memories):
    prompt = f"Memories: {memories}\nUser: {user_query}\nAI:"
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=500,
        temperature=0.5,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

---

## 🔧 Model-Agnostic Integration

### LLMClient Interface

```python
class LLMClient:
    def generate(self, prompt: str, system_prompt: str = "", model: str = None) -> str:
        raise NotImplementedError
```

### Provider Adapters

```python
class ClaudeClient(LLMClient):
    ...
class OpenAIClient(LLMClient):
    ...
class GeminiClient(LLMClient):
    ...
```

### Unified Prompt Usage

```python
llm: LLMClient = ClaudeClient()
prompt = build_augmented_prompt(memories, query)
llm.generate(prompt)
```

### Token Budget Trimming

```python
def trim_prompt(memories, query, model):
    # Use model-specific token limit to trim content
    ...
```

---

## 📢 EmbeddingClient Interface

```python
class EmbeddingClient:
    def embed(self, text: str) -> List[float]:
        raise NotImplementedError
```

Adapters:

- `OpenAIEmbedding`
- `HFEmbedding` (e.g. bge-base, MiniLM)

---

## 🏦 Config-Driven Runtime Switching

`.env` or config.yaml:

```env
LLM_PROVIDER=claude
EMBEDDING_PROVIDER=openai
```

Use this to dynamically load adapters at runtime.

---

## 📌 **9. Performance & Scalability Notes**

* For prototyping, use Chroma DB locally.
* For scale, switch to cloud-based vector DB (e.g., Pinecone, Weaviate).
* Implement efficient batch embeddings and pruning tasks.

---

## 📌 **10. Security & Privacy Guidelines**

* Secure API keys with environment variables.
* Consider data encryption for sensitive memory content.
* Include clear memory-deletion pathways for compliance (GDPR, etc.).

---

## 📌 **11. Acceptance Criteria**

* APIs functional with correct responses.
* Memories stored and retrieved accurately.
* Forgetting mechanism runs automatically.
* Integrated successfully with Claude API.
* Code is documented and easy to maintain.

---

## 📌 **12. Timeline**

| Parts | Task                                              |
| ----- | ------------------------------------------------- |
| 1-2   | API setup, embeddings, basic storage              |
| 3-4   | Retrieval logic, API testing                      |
| 5-6   | Forgetting mechanism, scheduled tasks             |
| 7-8   | Claude integration, full-cycle testing            |
| 9-10  | OpenAI 4o integration, full-cycle testing         |
| 11-12 | Google Gemini integration, full-cycle testing     |
| 12-14 | Documentation, performance testing, optimizations |
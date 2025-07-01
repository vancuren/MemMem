from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import asyncio

from src.memory_manager import MemoryManager
from src.models import StoreMemoryRequest, RetrieveMemoryRequest, ForgetMemoryRequest
from src.models import StoreMemoryResponse, RetrieveMemoryResponse, ForgetMemoryResponse, LLMRequest, LLMResponse
from src.scheduler import MemoryScheduler
from src.llm_client import create_llm_client, MemoryAugmentedLLM

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MemoryBank API",
    description="Long-term memory system for conversational AI agents",
    version="1.0.0"
)

security = HTTPBearer()
memory_manager = MemoryManager()
scheduler = MemoryScheduler(memory_manager)
llm_client = create_llm_client(os.getenv("LLM_PROVIDER", "claude"))
memory_augmented_llm = MemoryAugmentedLLM(llm_client, memory_manager)

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = os.getenv("API_KEY")
    if api_key and credentials.credentials != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials

@app.post("/store_memory", response_model=StoreMemoryResponse)
async def store_memory(
    request: StoreMemoryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        memory_id = await memory_manager.store_memory(request.content, request.metadata)
        return StoreMemoryResponse(memory_id=memory_id, status="stored")
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve_memory", response_model=RetrieveMemoryResponse)
async def retrieve_memory(
    request: RetrieveMemoryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        memories = await memory_manager.retrieve_memory(
            request.query, 
            request.top_k, 
            request.metadata
        )
        return RetrieveMemoryResponse(memories=memories)
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/forget_memory", response_model=ForgetMemoryResponse)
async def forget_memory(
    request: ForgetMemoryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        success = await memory_manager.forget_memory(request.memory_id)
        if success:
            return ForgetMemoryResponse(status="deleted", memory_id=request.memory_id)
        else:
            raise HTTPException(status_code=404, detail="Memory not found")
    except Exception as e:
        logger.error(f"Error forgetting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=LLMResponse)
async def chat_with_memory(
    request: LLMRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        result = await memory_augmented_llm.generate_with_memory(
            request.query,
            system_prompt=request.system_prompt or "",
            model=request.model
        )
        
        # Store the user's query as a memory
        await memory_manager.store_memory(
            f"User asked: {request.query}",
            {"type": "user_query", "timestamp": datetime.now().isoformat()}
        )
        
        # Store the assistant's response as a memory
        await memory_manager.store_memory(
            f"Assistant responded: {result['response']}",
            {"type": "assistant_response", "timestamp": datetime.now().isoformat()}
        )
        
        return LLMResponse(
            response=result["response"],
            model_used=result["model_info"]["default_model"],
            memories_used=result["memories_used"]
        )
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory_stats")
async def get_memory_stats(credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)):
    try:
        stats = await memory_manager.get_memory_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run_forgetting_curve")
async def run_forgetting_curve(credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)):
    try:
        await scheduler.run_forgetting_curve_now()
        return {"status": "forgetting curve applied", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error running forgetting curve: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scheduler_status")
async def get_scheduler_status(credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)):
    try:
        status = scheduler.get_scheduler_status()
        return status
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting MemoryBank API")
    # Start the memory scheduler
    scheduler.start_scheduler(
        forgetting_interval_hours=int(os.getenv("FORGETTING_INTERVAL_HOURS", "24")),
        maintenance_interval_hours=int(os.getenv("MAINTENANCE_INTERVAL_HOURS", "168"))
    )

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down MemoryBank API")
    scheduler.stop_scheduler()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
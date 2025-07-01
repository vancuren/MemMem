from fastapi import FastAPI, HTTPException, Depends, Header
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

# Global managers - will be initialized per tenant
tenant_managers: Dict[str, Dict[str, Any]] = {}

def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Extract tenant ID from header or environment variable"""
    tenant_id = x_tenant_id or os.getenv("TENANT_ID", "default")
    return tenant_id

def get_tenant_manager(tenant_id: str) -> MemoryManager:
    """Get or create tenant-specific memory manager"""
    if tenant_id not in tenant_managers:
        # Create tenant-specific database path
        base_path = os.getenv("CHROMA_DB_PATH", "./data")
        tenant_db_path = os.path.join(base_path, tenant_id, "memory_db")
        
        # Ensure directory exists
        os.makedirs(tenant_db_path, exist_ok=True)
        
        # Create tenant-specific manager
        memory_manager = MemoryManager(
            db_path=tenant_db_path,
            collection_name=f"memories_{tenant_id}"
        )
        
        scheduler = MemoryScheduler(memory_manager)
        llm_client = create_llm_client(os.getenv("LLM_PROVIDER", "claude"))
        memory_augmented_llm = MemoryAugmentedLLM(llm_client, memory_manager)
        
        tenant_managers[tenant_id] = {
            "memory_manager": memory_manager,
            "scheduler": scheduler,
            "memory_augmented_llm": memory_augmented_llm
        }
        
        logger.info(f"Created tenant manager for: {tenant_id}")
    
    return tenant_managers[tenant_id]

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = os.getenv("API_KEY")
    if api_key and credentials.credentials != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials

@app.post("/store_memory", response_model=StoreMemoryResponse)
async def store_memory(
    request: StoreMemoryRequest,
    tenant_id: str = Depends(get_tenant_id),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        tenant_data = get_tenant_manager(tenant_id)
        memory_manager = tenant_data["memory_manager"]
        memory_id = await memory_manager.store_memory(request.content, request.metadata)
        return StoreMemoryResponse(memory_id=memory_id, status="stored")
    except Exception as e:
        logger.error(f"Error storing memory for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve_memory", response_model=RetrieveMemoryResponse)
async def retrieve_memory(
    request: RetrieveMemoryRequest,
    tenant_id: str = Depends(get_tenant_id),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        tenant_data = get_tenant_manager(tenant_id)
        memory_manager = tenant_data["memory_manager"]
        memories = await memory_manager.retrieve_memory(
            request.query, 
            request.top_k, 
            request.metadata
        )
        return RetrieveMemoryResponse(memories=memories)
    except Exception as e:
        logger.error(f"Error retrieving memory for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/forget_memory", response_model=ForgetMemoryResponse)
async def forget_memory(
    request: ForgetMemoryRequest,
    tenant_id: str = Depends(get_tenant_id),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        tenant_data = get_tenant_manager(tenant_id)
        memory_manager = tenant_data["memory_manager"]
        success = await memory_manager.forget_memory(request.memory_id)
        if success:
            return ForgetMemoryResponse(status="deleted", memory_id=request.memory_id)
        else:
            raise HTTPException(status_code=404, detail="Memory not found")
    except Exception as e:
        logger.error(f"Error forgetting memory for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=LLMResponse)
async def chat_with_memory(
    request: LLMRequest,
    tenant_id: str = Depends(get_tenant_id),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        tenant_data = get_tenant_manager(tenant_id)
        memory_manager = tenant_data["memory_manager"]
        memory_augmented_llm = tenant_data["memory_augmented_llm"]
        
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
        logger.error(f"Error in chat for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory_stats")
async def get_memory_stats(
    tenant_id: str = Depends(get_tenant_id),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        tenant_data = get_tenant_manager(tenant_id)
        memory_manager = tenant_data["memory_manager"]
        stats = await memory_manager.get_memory_stats()
        stats["tenant_id"] = tenant_id
        return stats
    except Exception as e:
        logger.error(f"Error getting memory stats for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run_forgetting_curve")
async def run_forgetting_curve(
    tenant_id: str = Depends(get_tenant_id),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        tenant_data = get_tenant_manager(tenant_id)
        scheduler = tenant_data["scheduler"]
        await scheduler.run_forgetting_curve_now()
        return {
            "status": "forgetting curve applied", 
            "timestamp": datetime.now().isoformat(),
            "tenant_id": tenant_id
        }
    except Exception as e:
        logger.error(f"Error running forgetting curve for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scheduler_status")
async def get_scheduler_status(
    tenant_id: str = Depends(get_tenant_id),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    try:
        tenant_data = get_tenant_manager(tenant_id)
        scheduler = tenant_data["scheduler"]
        status = scheduler.get_scheduler_status()
        status["tenant_id"] = tenant_id
        return status
    except Exception as e:
        logger.error(f"Error getting scheduler status for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting MemoryBank API")
    # Initialize default tenant if specified
    tenant_id = os.getenv("TENANT_ID", "default")
    if tenant_id:
        logger.info(f"Initializing default tenant: {tenant_id}")
        tenant_data = get_tenant_manager(tenant_id)
        scheduler = tenant_data["scheduler"]
        scheduler.start_scheduler(
            forgetting_interval_hours=int(os.getenv("FORGETTING_INTERVAL_HOURS", "24")),
            maintenance_interval_hours=int(os.getenv("MAINTENANCE_INTERVAL_HOURS", "168"))
        )

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down MemoryBank API")
    # Stop all tenant schedulers
    for tenant_id, tenant_data in tenant_managers.items():
        logger.info(f"Stopping scheduler for tenant: {tenant_id}")
        scheduler = tenant_data["scheduler"]
        scheduler.stop_scheduler()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
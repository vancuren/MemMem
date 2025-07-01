from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging
import os
from typing import Optional
from datetime import datetime

from .memory_manager import MemoryManager
from .forgetting_curve import ForgettingCurve

logger = logging.getLogger(__name__)

class MemoryScheduler:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.forgetting_curve = ForgettingCurve(memory_manager.vector_store)
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def apply_forgetting_curve_job(self):
        try:
            logger.info("Starting scheduled forgetting curve application")
            result = await self.forgetting_curve.apply_forgetting_curve(
                decay_threshold=float(os.getenv("FORGETTING_THRESHOLD", "0.1"))
            )
            logger.info(f"Forgetting curve job completed: {result}")
        except Exception as e:
            logger.error(f"Error in forgetting curve job: {e}")
    
    async def memory_maintenance_job(self):
        try:
            logger.info("Starting memory maintenance job")
            
            # Get stats before maintenance
            stats_before = await self.memory_manager.get_memory_stats()
            logger.info(f"Memory stats before maintenance: {stats_before}")
            
            # Apply forgetting curve
            await self.apply_forgetting_curve_job()
            
            # Get stats after maintenance
            stats_after = await self.memory_manager.get_memory_stats()
            logger.info(f"Memory stats after maintenance: {stats_after}")
            
        except Exception as e:
            logger.error(f"Error in memory maintenance job: {e}")
    
    def start_scheduler(
        self, 
        forgetting_interval_hours: int = 24,
        maintenance_interval_hours: int = 168  # Weekly
    ):
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Schedule forgetting curve application (daily by default)
            self.scheduler.add_job(
                self.apply_forgetting_curve_job,
                trigger=IntervalTrigger(hours=forgetting_interval_hours),
                id="forgetting_curve_job",
                name="Apply Forgetting Curve",
                replace_existing=True
            )
            
            # Schedule comprehensive memory maintenance (weekly by default)
            self.scheduler.add_job(
                self.memory_maintenance_job,
                trigger=IntervalTrigger(hours=maintenance_interval_hours),
                id="memory_maintenance_job",
                name="Memory Maintenance",
                replace_existing=True
            )
            
            # Schedule immediate first run (after 1 minute)
            self.scheduler.add_job(
                self.apply_forgetting_curve_job,
                trigger=IntervalTrigger(minutes=1),
                id="initial_forgetting_job",
                name="Initial Forgetting Curve",
                max_instances=1
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"Memory scheduler started - Forgetting: every {forgetting_interval_hours}h, Maintenance: every {maintenance_interval_hours}h")
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
    
    def stop_scheduler(self):
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Memory scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    def get_scheduler_status(self):
        if not self.is_running:
            return {"status": "stopped", "jobs": []}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running",
            "jobs": jobs,
            "scheduler_state": self.scheduler.state
        }
    
    async def run_forgetting_curve_now(self):
        logger.info("Running forgetting curve manually")
        return await self.apply_forgetting_curve_job()
    
    async def run_maintenance_now(self):
        logger.info("Running memory maintenance manually")
        return await self.memory_maintenance_job()
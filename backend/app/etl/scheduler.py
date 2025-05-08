"""
Scheduler for running ETL jobs on a regular basis.
This module schedules nightly data processing to keep market data fresh.
"""
import asyncio
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

from .data_processor import market_data_processor

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ETLScheduler:
    """
    Scheduler for running ETL jobs at specified intervals
    """
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        
        # Get schedule from environment variables
        self.schedule_hour = int(os.getenv("ETL_SCHEDULE_HOUR", 1))
        self.schedule_minute = int(os.getenv("ETL_SCHEDULE_MINUTE", 0))
    
    def start(self):
        """Start the scheduler in a separate thread"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("ETL scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1.0)
        
        logger.info("ETL scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop - runs in a separate thread"""
        logger.info(f"Scheduler thread started, will run at {self.schedule_hour:02d}:{self.schedule_minute:02d}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.is_running:
            now = datetime.now()
            
            # Check if it's time to run the ETL job (using configured schedule)
            if now.hour == self.schedule_hour and now.minute == self.schedule_minute:
                logger.info("Running scheduled ETL job")
                
                # Run the ETL job
                try:
                    loop.run_until_complete(self._run_etl_job())
                except Exception as e:
                    logger.error(f"Error running ETL job: {str(e)}")
                
                # Wait until the next minute before checking again to avoid multiple runs
                time.sleep(60)
            else:
                # Calculate seconds until next run
                next_run = now.replace(
                    hour=self.schedule_hour, 
                    minute=self.schedule_minute,
                    second=0, 
                    microsecond=0
                )
                
                if next_run <= now:
                    # If the scheduled time has already passed today, schedule for tomorrow
                    next_run = next_run + timedelta(days=1)
                
                # Calculate seconds until next run
                seconds_until_next_run = (next_run - now).total_seconds()
                
                # Log when next run will be
                logger.debug(f"Next ETL job will run in {seconds_until_next_run/3600:.2f} hours")
                
                # Sleep for a while (check every minute)
                time.sleep(min(60, seconds_until_next_run))
        
        loop.close()
        logger.info("Scheduler thread stopped")
    
    async def _run_etl_job(self):
        """Run the ETL job"""
        logger.info("Starting scheduled ETL job")
        
        try:
            # Process all market data
            await market_data_processor.process_all_data()
            
            logger.info("Scheduled ETL job completed successfully")
        except Exception as e:
            logger.error(f"Error in scheduled ETL job: {str(e)}")
            # Continue execution - don't let exceptions stop the scheduler
    
    def run_now(self):
        """Run the ETL job immediately (manual trigger)"""
        logger.info("Manual ETL job triggered")
        
        # Don't use run_until_complete if already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're already in an event loop, so we should create a task instead
            return asyncio.create_task(self._run_etl_job())
        except RuntimeError:
            # No event loop running, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._run_etl_job())


# Singleton instance
etl_scheduler = ETLScheduler()
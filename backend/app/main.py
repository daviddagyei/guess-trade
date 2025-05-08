from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import logging
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import ETL components
from app.etl.scheduler import etl_scheduler
from app.cache.redis_cache import redis_cache
from app.api_clients.market_data import market_data_client

app = FastAPI(
    title="GuessTrade API",
    description="Trading chart game API",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    logger.info("Starting up GuessTrade API")
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Start the ETL scheduler
    etl_scheduler.start()
    logger.info("ETL scheduler started")
    
    # Run initial data processing if needed
    if os.getenv("RUN_INITIAL_ETL", "false").lower() == "true":
        logger.info("Running initial ETL process")
        etl_scheduler.run_now()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up services on application shutdown"""
    logger.info("Shutting down GuessTrade API")
    
    # Stop the ETL scheduler
    etl_scheduler.stop()
    logger.info("ETL scheduler stopped")

@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"status": "ok", "message": "GuessTrade API is running"}

@app.get("/api/health")
async def health_check():
    """Detailed health check endpoint"""
    # Check Redis connection
    redis_status = "ok"
    memory_cache_status = "ok"
    system_health = "ok"
    
    # Check Redis cache availability
    try:
        redis_is_available = redis_cache.redis.is_available()
        if not redis_is_available:
            redis_status = "unavailable - using memory fallback"
            # System is still healthy if memory cache is working
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    # Always report memory cache status
    try:
        # Verify memory cache by setting and getting a test value
        test_key = "_health_check_test"
        test_value = {"timestamp": time.time()}
        memory_set_success = redis_cache.memory.set_data(test_key, test_value, 60)
        memory_get_result = redis_cache.memory.get_data(test_key)
        
        if not memory_set_success or not memory_get_result:
            memory_cache_status = "error: operation failed"
            # If both Redis and memory cache are down, system is unhealthy
            if redis_status != "ok":
                system_health = "error"
    except Exception as e:
        memory_cache_status = f"error: {str(e)}"
        # If both Redis and memory cache are down, system is unhealthy
        if redis_status != "ok":
            system_health = "error"
        
    return {
        "status": system_health,
        "version": app.version,
        "services": {
            "redis": redis_status,
            "memory_cache": memory_cache_status
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    try:
        while True:
            # Echo back received messages for testing
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()

# Import and include API routers
from app.routers import game
app.include_router(game.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
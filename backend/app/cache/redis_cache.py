"""
Redis Cache Manager for storing and retrieving market data
"""
import os
import json
import logging
import redis
from typing import Any, Optional, Dict, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis cache for storing and retrieving data"""
    
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD")
        
        # Connect to Redis
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True
        )
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
    
    def set_data(self, key: str, data: Any, ttl_seconds: int = 3600) -> bool:
        """
        Store data in Redis cache
        
        Args:
            key: Cache key
            data: Data to cache (will be JSON serialized)
            ttl_seconds: Time to live in seconds (default: 1 hour)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            serialized_data = json.dumps(data)
            self.redis_client.setex(key, ttl_seconds, serialized_data)
            return True
        except (redis.exceptions.RedisError, TypeError) as e:
            logger.error(f"Error setting cache for {key}: {str(e)}")
            return False
    
    def get_data(self, key: str) -> Optional[Any]:
        """
        Retrieve data from Redis cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached data if found, None otherwise
        """
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except (redis.exceptions.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cache for {key}: {str(e)}")
            return None
    
    def delete_data(self, key: str) -> bool:
        """
        Delete data from Redis cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.redis_client.delete(key)
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Error deleting cache for {key}: {str(e)}")
            return False
    
    def build_market_data_key(self, symbol: str, data_type: str, interval: str = None) -> str:
        """
        Build a standardized key for market data
        
        Args:
            symbol: Market symbol (e.g., AAPL, BTC)
            data_type: Type of data (e.g., daily, intraday, crypto)
            interval: Time interval for intraday data
            
        Returns:
            Formatted cache key
        """
        if data_type == "intraday" and interval:
            return f"market_data:{symbol}:{data_type}:{interval}"
        return f"market_data:{symbol}:{data_type}"


# Singleton instance
redis_cache = RedisCache()
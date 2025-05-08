"""
Cache Manager with Redis and in-memory fallback for storing and retrieving market data
"""
import os
import json
import logging
import redis
import time
import asyncio
from typing import Any, Optional, Dict, Union, List
from abc import ABC, abstractmethod
from collections import OrderedDict
from dotenv import load_dotenv
from threading import RLock
from functools import partial

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class CacheBase(ABC):
    """Base interface for all cache implementations"""
    
    @abstractmethod
    async def set_data(self, key: str, data: Any, ttl_seconds: int = 3600) -> bool:
        """Store data in cache"""
        pass
    
    @abstractmethod
    async def get_data(self, key: str) -> Optional[Any]:
        """Retrieve data from cache"""
        pass
    
    @abstractmethod
    async def delete_data(self, key: str) -> bool:
        """Delete data from cache"""
        pass
    
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


class RedisCache(CacheBase):
    """Redis cache for storing and retrieving data"""
    
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD")
        
        # Connect to Redis
        self._client = None
        self._is_connected = False
        
        # Initialize the connection synchronously instead of using asyncio.create_task
        try:
            # Create the Redis client
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            
            # Try a synchronous ping to test connection
            if client.ping():
                self._client = client
                self._is_connected = True
                logger.info("Successfully connected to Redis")
            else:
                logger.error("Failed to connect to Redis: ping returned False")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._is_connected = False
    
    # The connect method can still be used for reconnection attempts
    async def connect(self, host: str, port: int, password: Optional[str] = None) -> bool:
        """
        Connect to Redis server
        
        Returns:
            bool: True if successfully connected, False otherwise
        """
        try:
            # Create the Redis client
            client = redis.Redis(
                host=host,
                port=port,
                password=password,
                decode_responses=True,
                socket_timeout=2.0,  # Set timeout to avoid hanging
                socket_connect_timeout=2.0
            )
            
            # Check connection in a non-blocking way
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, client.ping)
            
            self._client = client
            self._is_connected = True
            logger.info("Successfully connected to Redis")
            return True
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._is_connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {str(e)}")
            self._is_connected = False
            return False
    
    async def is_available(self) -> bool:
        """
        Check if Redis is available
        
        Returns:
            bool: True if Redis is available, False otherwise
        """
        if not self._is_connected or self._client is None:
            return False
            
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._client.ping)
        except Exception:
            self._is_connected = False
            return False
    
    async def set_data(self, key: str, data: Any, ttl_seconds: int = 3600) -> bool:
        """
        Store data in Redis cache
        
        Args:
            key: Cache key
            data: Data to cache (will be JSON serialized)
            ttl_seconds: Time to live in seconds (default: 1 hour)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not await self.is_available():
            logger.warning("Redis not available for setting data")
            return False
        
        try:
            serialized_data = json.dumps(data)
            loop = asyncio.get_running_loop()
            
            # Use run_in_executor to avoid blocking the event loop
            await loop.run_in_executor(
                None, 
                partial(self._client.setex, key, ttl_seconds, serialized_data)
            )
            return True
        except (redis.exceptions.RedisError, TypeError) as e:
            logger.error(f"Error setting cache for {key}: {str(e)}")
            return False
    
    async def get_data(self, key: str) -> Optional[Any]:
        """
        Retrieve data from Redis cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached data if found, None otherwise
        """
        if not await self.is_available():
            logger.warning("Redis not available for getting data")
            return None
        
        try:
            loop = asyncio.get_running_loop()
            
            # Use run_in_executor to avoid blocking the event loop
            data = await loop.run_in_executor(None, self._client.get, key)
            
            if data:
                return json.loads(data)
            return None
        except (redis.exceptions.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting cache for {key}: {str(e)}")
            return None
    
    async def delete_data(self, key: str) -> bool:
        """
        Delete data from Redis cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not await self.is_available():
            logger.warning("Redis not available for deleting data")
            return False
        
        try:
            loop = asyncio.get_running_loop()
            
            # Use run_in_executor to avoid blocking the event loop
            await loop.run_in_executor(None, self._client.delete, key)
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Error deleting cache for {key}: {str(e)}")
            return False


class MemoryCache(CacheBase):
    """In-memory cache for storing and retrieving data"""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize in-memory cache
        
        Args:
            max_size: Maximum number of items to store in cache (default: 1000)
        """
        self._cache = OrderedDict()  # Use OrderedDict for LRU functionality
        self._ttl = {}  # Store expiration timestamps
        self._max_size = max_size
        self._lock = RLock()  # For thread safety
        logger.info("In-memory cache initialized")
    
    def _cleanup_expired(self):
        """Remove expired items from cache"""
        now = time.time()
        expired_keys = [k for k, exp in self._ttl.items() if exp <= now]
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._ttl.pop(key, None)
    
    async def set_data(self, key: str, data: Any, ttl_seconds: int = 3600) -> bool:
        """
        Store data in memory cache
        
        Args:
            key: Cache key
            data: Data to cache
            ttl_seconds: Time to live in seconds (default: 1 hour)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # For potentially expensive operations, run in executor
            loop = asyncio.get_running_loop()
            
            def _set_data():
                with self._lock:
                    # Clean up expired items first
                    self._cleanup_expired()
                    
                    # Enforce max size by removing oldest items if needed (LRU eviction)
                    while len(self._cache) >= self._max_size:
                        self._cache.popitem(last=False)  # Remove oldest item
                        
                    # Store data and TTL
                    self._cache[key] = data
                    self._ttl[key] = time.time() + ttl_seconds
                    
                return True
                
            return await loop.run_in_executor(None, _set_data)
            
        except Exception as e:
            logger.error(f"Error setting memory cache for {key}: {str(e)}")
            return False
    
    async def get_data(self, key: str) -> Optional[Any]:
        """
        Retrieve data from memory cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached data if found and not expired, None otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            
            def _get_data():
                with self._lock:
                    # Check if item exists and isn't expired
                    if key in self._cache and time.time() <= self._ttl.get(key, 0):
                        # Move to end for LRU tracking
                        self._cache.move_to_end(key)
                        return self._cache[key]
                    
                    # If item doesn't exist or is expired, remove it
                    if key in self._cache:
                        self._cache.pop(key, None)
                        self._ttl.pop(key, None)
                    
                    return None
            
            return await loop.run_in_executor(None, _get_data)
            
        except Exception as e:
            logger.error(f"Error getting memory cache for {key}: {str(e)}")
            return None
    
    async def delete_data(self, key: str) -> bool:
        """
        Delete data from memory cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            
            def _delete_data():
                with self._lock:
                    if key in self._cache:
                        self._cache.pop(key, None)
                        self._ttl.pop(key, None)
                return True
            
            return await loop.run_in_executor(None, _delete_data)
            
        except Exception as e:
            logger.error(f"Error deleting memory cache for {key}: {str(e)}")
            return False


class CompositeCache(CacheBase):
    """Composite cache that tries Redis first, then falls back to in-memory"""
    
    def __init__(self, redis_cache: RedisCache, memory_cache: MemoryCache):
        """
        Initialize composite cache with Redis and in-memory caches
        
        Args:
            redis_cache: Redis cache implementation
            memory_cache: In-memory cache implementation
        """
        self.redis = redis_cache
        self.memory = memory_cache
        self._redis_unavailable_since = None
        self._retry_interval = 60  # seconds to wait before retrying Redis after failure
        logger.info("Composite cache initialized")
    
    async def _should_try_redis(self) -> bool:
        """
        Check if we should try Redis or skip directly to memory cache
        
        Returns:
            bool: True if we should try Redis, False otherwise
        """
        # If Redis was never unavailable, try it
        if not self._redis_unavailable_since:
            return True
            
        # If retry interval has passed, try Redis again
        if time.time() - self._redis_unavailable_since > self._retry_interval:
            return True
            
        # Otherwise, skip Redis
        return False
    
    async def set_data(self, key: str, data: Any, ttl_seconds: int = 3600) -> bool:
        """
        Store data in cache (tries Redis first, then memory)
        
        Args:
            key: Cache key
            data: Data to cache
            ttl_seconds: Time to live in seconds (default: 1 hour)
            
        Returns:
            bool: True if successful in any cache, False if failed in all
        """
        redis_success = False
        
        # Try Redis first if it should be available
        if await self._should_try_redis():
            redis_success = await self.redis.set_data(key, data, ttl_seconds)
            
            # Update Redis availability status
            if not redis_success:
                if not self._redis_unavailable_since:
                    self._redis_unavailable_since = time.time()
                    logger.warning("Redis became unavailable, using memory cache fallback")
            else:
                # Redis is working, reset unavailable timestamp
                self._redis_unavailable_since = None
        
        # Always set in memory cache as a backup
        memory_success = await self.memory.set_data(key, data, ttl_seconds)
        
        return redis_success or memory_success
    
    async def get_data(self, key: str) -> Optional[Any]:
        """
        Retrieve data from cache (tries Redis first, then memory)
        
        Args:
            key: Cache key
            
        Returns:
            Cached data if found in any cache, None otherwise
        """
        # Try Redis first if it should be available
        if await self._should_try_redis():
            try:
                redis_data = await self.redis.get_data(key)
                
                # Redis is working, reset unavailable timestamp
                if redis_data is not None:
                    self._redis_unavailable_since = None
                    return redis_data
                    
            except Exception as e:
                logger.error(f"Error retrieving data from Redis: {str(e)}")
                # Mark Redis as unavailable
                if not self._redis_unavailable_since:
                    self._redis_unavailable_since = time.time()
                    logger.warning("Redis became unavailable, using memory cache fallback")
        
        # Fall back to memory cache
        return await self.memory.get_data(key)
    
    async def delete_data(self, key: str) -> bool:
        """
        Delete data from both caches
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful in any cache, False if failed in all
        """
        redis_success = False
        
        # Try Redis first if it should be available
        if await self._should_try_redis():
            redis_success = await self.redis.delete_data(key)
            
            # Update Redis availability status
            if not redis_success:
                if not self._redis_unavailable_since:
                    self._redis_unavailable_since = time.time()
                    logger.warning("Redis became unavailable, using memory cache fallback")
            else:
                # Redis is working, reset unavailable timestamp
                self._redis_unavailable_since = None
        
        # Always delete from memory cache too
        memory_success = await self.memory.delete_data(key)
        
        return redis_success or memory_success


# Create individual cache instances
_redis_cache = RedisCache()
_memory_cache = MemoryCache(max_size=1000)  # Adjust size based on your memory constraints

# Create and export the composite cache as the singleton instance
redis_cache = CompositeCache(_redis_cache, _memory_cache)
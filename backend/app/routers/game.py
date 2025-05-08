from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import List, Dict, Any, Optional
import json
import logging

from ..cache.redis_cache import redis_cache
from ..etl.data_processor import market_data_processor
from ..technical_analysis.indicators import technical_indicators

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/game",
    tags=["game"],
    responses={404: {"description": "Not found"}}
)

class ConnectionManager:
    """Manager for WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def send_json(self, websocket: WebSocket, data: Dict[str, Any]):
        await websocket.send_text(json.dumps(data))

manager = ConnectionManager()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # For milestone 1, we'll just echo the message
            await manager.send_json(websocket, {
                "message": f"Server received: {data}",
                "client_id": client_id
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"Client #{client_id} disconnected")

# New endpoints for market data and technical indicators

@router.get("/market-data/stocks")
async def get_available_stocks():
    """Get list of available stock symbols"""
    return {"symbols": market_data_processor.stock_symbols}

@router.get("/market-data/crypto")
async def get_available_crypto():
    """Get list of available cryptocurrency symbols"""
    return {"symbols": market_data_processor.crypto_symbols}

@router.get("/market-data/stock/{symbol}")
async def get_stock_data(symbol: str):
    """
    Get stock market data for a specific symbol
    """
    # Normalize symbol to uppercase
    symbol = symbol.upper()
    
    # Check if this is a valid symbol
    if symbol not in market_data_processor.stock_symbols:
        raise HTTPException(status_code=404, detail=f"Stock symbol '{symbol}' not found")
    
    # Try to get data from cache first
    cache_key = redis_cache.build_market_data_key(symbol, "daily")
    cached_data = redis_cache.get_data(cache_key)
    
    if cached_data:
        logger.info(f"Returning cached stock data for {symbol}")
        return cached_data
    
    # If not in cache, fetch and process it
    logger.info(f"Fetching and processing stock data for {symbol}")
    processed_data = await market_data_processor.process_stock_data(symbol)
    
    if not processed_data:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data for {symbol}")
    
    return processed_data

@router.get("/market-data/crypto/{symbol}")
async def get_crypto_data(symbol: str):
    """
    Get cryptocurrency market data for a specific symbol
    """
    # Normalize symbol to uppercase
    symbol = symbol.upper()
    
    # Check if this is a valid symbol
    if symbol not in market_data_processor.crypto_symbols:
        raise HTTPException(status_code=404, detail=f"Crypto symbol '{symbol}' not found")
    
    # Try to get data from cache first
    cache_key = redis_cache.build_market_data_key(symbol, "crypto")
    cached_data = redis_cache.get_data(cache_key)
    
    if cached_data:
        logger.info(f"Returning cached crypto data for {symbol}")
        return cached_data
    
    # If not in cache, fetch and process it
    logger.info(f"Fetching and processing crypto data for {symbol}")
    processed_data = await market_data_processor.process_crypto_data(symbol)
    
    if not processed_data:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data for {symbol}")
    
    return processed_data

@router.get("/indicators/{asset_type}/{symbol}")
async def get_technical_indicators(asset_type: str, symbol: str):
    """
    Get technical indicators for a specific symbol
    
    Args:
        asset_type: "stock" or "crypto"
        symbol: Asset symbol (e.g., AAPL, BTC)
    """
    # Normalize inputs
    asset_type = asset_type.lower()
    symbol = symbol.upper()
    
    # Validate asset type
    if asset_type not in ["stock", "crypto"]:
        raise HTTPException(status_code=400, detail="Asset type must be 'stock' or 'crypto'")
    
    # Validate symbol
    valid_symbols = market_data_processor.stock_symbols if asset_type == "stock" else market_data_processor.crypto_symbols
    if symbol not in valid_symbols:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found for {asset_type}")
    
    # Try to get indicators from cache
    cache_key = f"indicators:{asset_type}:{symbol}"
    cached_indicators = redis_cache.get_data(cache_key)
    
    if cached_indicators:
        logger.info(f"Returning cached indicators for {asset_type}:{symbol}")
        return cached_indicators
    
    # If not cached, we need to calculate them
    # First, get the market data
    if asset_type == "stock":
        market_data = await get_stock_data(symbol)
    else:
        market_data = await get_crypto_data(symbol)
    
    if not market_data:
        raise HTTPException(status_code=500, detail=f"Failed to get market data for {symbol}")
    
    # Calculate indicators
    logger.info(f"Calculating indicators for {asset_type}:{symbol}")
    indicators = await market_data_processor._calculate_technical_indicators(
        symbol, market_data, asset_type=asset_type
    )
    
    return indicators
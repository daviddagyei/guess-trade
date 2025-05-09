from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import List, Dict, Any, Optional
import json
import logging
import uuid
import time
import asyncio

from ..cache.redis_cache import redis_cache
from ..etl.data_processor import market_data_processor
from ..services.game_engine import GameEngine

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/game",
    tags=["game"],
    responses={404: {"description": "Not found"}}
)

# Initialize game engine
game_engine = GameEngine()

class ConnectionManager:
    """Manager for WebSocket connections with heartbeat support"""
    
    def __init__(self, heartbeat_interval: int = 10, heartbeat_timeout: int = 30):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, str] = {}  # Map client_id to session_id
        self.last_activity: Dict[str, float] = {}  # Timestamp of last message
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.heartbeat_task = None
    
    async def start_heartbeat(self):
        """Start the heartbeat loop as an async task"""
        if self.heartbeat_task is None:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("Heartbeat loop started")
    
    async def _heartbeat_loop(self):
        """Loop to check for stale connections and send pings"""
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            now = time.time()
            to_disconnect: List[str] = []
            for client_id, ws in list(self.active_connections.items()):
                last = self.last_activity.get(client_id, now)
                # If no activity within timeout, mark for disconnect
                if now - last > self.heartbeat_timeout:
                    to_disconnect.append(client_id)
                else:
                    # send ping to client
                    try:
                        await ws.send_text(json.dumps({"type": "ping"}))
                    except Exception:
                        to_disconnect.append(client_id)
            # Disconnect stale or errored clients
            for client_id in to_disconnect:
                ws = self.active_connections.get(client_id)
                if ws:
                    await ws.close()
                self.disconnect(client_id)
                logger.info(f"Disconnected stale client: {client_id}")
    
    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.last_activity[client_id] = time.time()
        logger.info(f"Client connected: {client_id}")
        # Ensure heartbeat is running whenever a client connects
        await self.start_heartbeat()
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client disconnected: {client_id}")
        if client_id in self.last_activity:
            del self.last_activity[client_id]
        if client_id in self.sessions:
            del self.sessions[client_id]
    
    async def send_json(self, client_id: str, data: Dict[str, Any]):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(json.dumps(data))
            self.last_activity[client_id] = time.time()
    
    def register_session(self, client_id: str, session_id: str):
        self.sessions[client_id] = session_id
        logger.info(f"Registered session {session_id} for client {client_id}")
    
    def get_session_id(self, client_id: str) -> Optional[str]:
        return self.sessions.get(client_id)
    
    def update_activity(self, client_id: str):
        self.last_activity[client_id] = time.time()

manager = ConnectionManager()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            manager.update_activity(client_id)
            message = json.loads(data)
            # Handle heartbeat pong from client
            if message.get("type") == "pong":
                continue
            
            action = message.get("action")
            
            if action == "start_game":
                # Generate a new game session
                difficulty = message.get("difficulty", 1)
                session_id = str(uuid.uuid4())
                
                # Register this session with the client
                manager.register_session(client_id, session_id)
                
                # Seed the game
                game_data = await game_engine.seed_game(session_id, difficulty)
                
                # Send game data to client
                await manager.send_json(client_id, {
                    "type": "game_start",
                    "session_id": session_id,
                    "game_data": game_data
                })
                
            elif action == "submit_answer":
                # Process the player's guess
                session_id = manager.get_session_id(client_id)
                
                if not session_id:
                    await manager.send_json(client_id, {
                        "type": "error",
                        "message": "No active game session"
                    })
                    continue
                
                # Get answer from message
                user_answer = message.get("answer")
                
                if user_answer is None:
                    await manager.send_json(client_id, {
                        "type": "error",
                        "message": "No answer provided"
                    })
                    continue
                
                # Process the user's guess
                result = game_engine.submit_guess(session_id, user_answer)
                
                # Send result to client
                await manager.send_json(client_id, {
                    "type": "game_result",
                    "result": result
                })
                
            elif action == "get_game_state":
                # Retrieve the current game state
                session_id = manager.get_session_id(client_id)
                
                if not session_id:
                    await manager.send_json(client_id, {
                        "type": "error",
                        "message": "No active game session"
                    })
                    continue
                
                # Get the game state
                game_state = game_engine.get_game_state(session_id)
                
                # Send game state to client
                await manager.send_json(client_id, {
                    "type": "game_state",
                    "game_state": game_state
                })
                
            else:
                # Echo back unknown messages with a note
                await manager.send_json(client_id, {
                    "type": "message",
                    "message": f"Received unknown action: {action}",
                    "data": message
                })
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
        manager.disconnect(client_id)

# Keep the existing REST endpoints for market data and technical indicators

# New endpoints for game management via HTTP (in addition to WebSocket)

@router.post("/sessions")
async def create_game_session(difficulty: int = 1):
    """Create a new game session via HTTP"""
    session_id = str(uuid.uuid4())
    game_data = await game_engine.seed_game(session_id, difficulty)
    
    return {
        "session_id": session_id,
        "game_data": game_data
    }

@router.post("/sessions/{session_id}/guess")
async def submit_guess(session_id: str, answer: int):
    """Submit a guess for a game session via HTTP"""
    result = game_engine.submit_guess(session_id, answer)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@router.get("/sessions/{session_id}")
async def get_game_session(session_id: str):
    """Get the current state of a game session via HTTP"""
    game_state = game_engine.get_game_state(session_id)
    
    if "error" in game_state:
        raise HTTPException(status_code=404, detail=game_state["error"])
        
    return game_state

@router.get("/market-data/stocks")
async def get_available_stocks():
    """Get list of available stock symbols"""
    return {"symbols": market_data_processor.stock_symbols}

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
    cached_data = await redis_cache.get_data(cache_key)
    
    if cached_data:
        logger.info(f"Returning cached stock data for {symbol}")
        return cached_data
    
    # If not in cache, fetch and process it
    logger.info(f"Fetching and processing stock data for {symbol}")
    processed_data = await market_data_processor.process_stock_data(symbol)
    
    if not processed_data:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data for {symbol}")
    
    return processed_data
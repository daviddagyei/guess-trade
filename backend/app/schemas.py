from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
from enum import Enum


class AssetType(str, Enum):
    """Valid asset types for the game"""
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"


class TimeFrame(str, Enum):
    """Valid timeframes for market data"""
    ONE_MIN = "1m"
    FIVE_MIN = "5m"
    FIFTEEN_MIN = "15m"
    THIRTY_MIN = "30m"
    ONE_HOUR = "1h"
    FOUR_HOUR = "4h"
    DAILY = "1d"
    WEEKLY = "1w"


class OutputSize(str, Enum):
    """Valid output sizes for market data"""
    COMPACT = "compact"
    FULL = "full"


# Market Data Models
class MarketDataEntry(BaseModel):
    """Model for a single market data point"""
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    
    @validator('*')
    def validate_prices(cls, v, values, **kwargs):
        """Ensure price data is valid"""
        field = kwargs.get('field')
        if field in ['open', 'high', 'low', 'close'] and v <= 0:
            raise ValueError(f"{field} must be positive")
        return v
    
    @root_validator
    def validate_price_consistency(cls, values):
        """Validate consistency between prices"""
        if all(k in values for k in ['low', 'high', 'open', 'close']):
            high, low = values['high'], values['low']
            open_price, close = values['open'], values['close']
            
            if low > high:
                raise ValueError("Low price cannot be higher than high price")
            if open_price < low or open_price > high:
                raise ValueError("Open price must be within low-high range")
            if close < low or close > high:
                raise ValueError("Close price must be within low-high range")
        return values


class MarketDataMetadata(BaseModel):
    """Metadata for market data responses"""
    symbol: str = Field(..., description="Trading symbol")
    last_refreshed: datetime = Field(..., description="Last data refresh time")
    time_zone: str = Field(..., description="Timezone of the data")
    interval: Optional[str] = Field(None, description="Data interval if applicable")
    information: str = Field(..., description="Information about the data")


class TimeSeriesData(BaseModel):
    """Time series data with validation"""
    meta_data: MarketDataMetadata
    time_series: Dict[str, MarketDataEntry] = Field(
        ..., 
        description="Timestamp to market data mapping"
    )
    
    @validator('time_series')
    def validate_time_series_not_empty(cls, v):
        """Ensure we have at least some data points"""
        if not v:
            raise ValueError("Time series data cannot be empty")
        return v


# Game Models
class GameOption(BaseModel):
    """Single game option model"""
    id: int = Field(..., ge=0, description="Option ID")
    data: List[Dict[str, Union[str, float]]] = Field(..., description="Option data points")
    is_correct: Optional[bool] = Field(None, description="Whether this is the correct answer")


class GameOverlay(BaseModel):
    """Technical indicator overlay for game charts"""
    type: str = Field(..., description="Type of indicator")
    data: Dict[str, List[Optional[float]]] = Field(..., description="Indicator data")


class GameSetup(BaseModel):
    """Game chart setup data"""
    timestamp: List[str] = Field(..., min_items=1, description="Timestamps for data points")
    base_data: Dict[str, List[float]] = Field(..., description="OHLCV data")


class GameSessionRequest(BaseModel):
    """Request to create a new game session"""
    difficulty: int = Field(1, ge=1, le=5, description="Game difficulty level (1-5)")
    asset_type: Optional[AssetType] = Field(None, description="Type of asset to use")
    instrument: Optional[str] = Field(None, description="Specific instrument (e.g. AAPL)")


class GameSessionResponse(BaseModel):
    """Response containing game session data"""
    session_id: str = Field(..., description="Unique session identifier") 
    asset_type: AssetType
    instrument: str = Field(..., min_length=1, description="Trading instrument")
    timeframe: TimeFrame
    difficulty: int = Field(..., ge=1, le=5, description="Difficulty level")
    setup: GameSetup
    overlays: Dict[str, GameOverlay] = Field(default_factory=dict)
    options: List[GameOption]
    start_time: datetime
    status: str = Field(..., description="Game status (active/completed)")
    
    @validator('options')
    def validate_options(cls, v):
        """Ensure we have 2-4 options"""
        if not 2 <= len(v) <= 4:
            raise ValueError("Game must have between 2 and 4 options")
        return v


class GuessSubmission(BaseModel):
    """User guess submission"""
    session_id: str = Field(..., description="Game session ID")
    user_answer: int = Field(..., ge=0, description="Selected option ID")


class GuessResult(BaseModel):
    """Result of a user's guess"""
    session_id: str
    is_correct: bool
    score: int = Field(..., ge=0, description="Points earned")
    time_taken: float = Field(..., ge=0, description="Time taken in seconds")
    correct_option: int


class ErrorResponse(BaseModel):
    """Standardized error response"""
    error: str
    detail: Optional[str] = None
    
    
# Market Data Request Models
class MarketDataRequest(BaseModel):
    """Base model for market data requests"""
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")


class DailyTimeSeriesRequest(MarketDataRequest):
    """Request for daily time series data"""
    output_size: OutputSize = Field(default=OutputSize.COMPACT)


class IntradayDataRequest(MarketDataRequest):
    """Request for intraday time series data"""
    interval: TimeFrame = Field(default=TimeFrame.FIVE_MIN)


class CryptoDataRequest(MarketDataRequest):
    """Request for cryptocurrency data"""
    market: str = Field(default="USD", min_length=3, max_length=5)
    
    @validator('symbol')
    def validate_crypto_symbol(cls, v):
        """Ensure crypto symbol is uppercase and valid"""
        v = v.upper()
        if not v.isalpha() or len(v) > 5:
            raise ValueError("Invalid cryptocurrency symbol")
        return v
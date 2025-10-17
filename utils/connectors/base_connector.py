from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json
import os

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"

@dataclass
class Price:
    symbol: str
    price: float
    timestamp: datetime

@dataclass
class FundingRate:
    symbol: str
    rate: float
    timestamp: datetime
    next_funding_time: Optional[datetime] = None

@dataclass
class Order:
    """
    Immutable record of trade execution parameters for logging and analysis.
    Orders are created upon trade execution and logged to persistent storage.
    Not used for ongoing order management - use get_open_positions() for current state.
    """
    id: str                           # Exchange-provided order identifier
    symbol: str                       # Trading pair symbol
    side: OrderSide                   # BUY or SELL direction
    type: OrderType                   # Order type (MARKET for our use case)
    size: float                       # Actual filled size in traded asset units
    price: Optional[float]            # Actual execution price (None if pending)
    status: OrderStatus               # PENDING, FILLED, or PARTIAL
    timestamp: datetime               # Order creation/execution timestamp

@dataclass
class Position:
    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    timestamp: datetime
    leverage: float = 1.0  # Default 1x leverage

class BaseDEXConnector(ABC):
    def __init__(self, api_key: str = None, secret_key: str = None, **kwargs):
        self.api_key = api_key
        self.secret_key = secret_key
        self.extra_params = kwargs
        
        # Trade logging setup
        self.trade_log_dir = kwargs.get('trade_log_dir', 'logs/trades')
        os.makedirs(self.trade_log_dir, exist_ok=True)
        
        # DEX-specific trade log file
        dex_name = self.__class__.__name__.replace('Connector', '').lower()
        self.trade_log_file = os.path.join(self.trade_log_dir, f'{dex_name}_trades.jsonl')
    
    def _log_trade(self, order: 'Order') -> None:
        """Log completed trade to persistent storage"""
        try:
            trade_entry = {
                'timestamp': order.timestamp.isoformat(),
                'order_id': order.id,
                'symbol': order.symbol,
                'side': order.side.value,
                'type': order.type.value,
                'size': order.size,
                'price': order.price,
                'status': order.status.value,
                'dex': self.__class__.__name__.replace('Connector', '').lower()
            }
            
            with open(self.trade_log_file, 'a') as f:
                f.write(json.dumps(trade_entry) + '\n')
        except Exception as e:
            # Don't let logging errors break trading operations
            pass  # Ignore logging errors
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Price:
        pass
    
    @abstractmethod
    async def get_current_funding_rate(self, symbol: str) -> FundingRate:
        pass
    

    @abstractmethod
    async def get_current_leverage(self) -> int:
        pass

    @abstractmethod
    async def set_leverage(self, newLeverage: int, symbol: Optional[str] = None) -> int:
        pass

    @abstractmethod
    async def get_min_order_size(self, symbol: str) -> float:
        # Returns minimum order size denominated in the traded asset, not USD
        pass
    
    @abstractmethod
    async def place_market_buy_order(self, symbol: str, size: float, slippage: float) -> Order:
        """
        Place a market buy order with explicit slippage protection.
        
        Args:
            symbol: Trading pair symbol
            size: Order size in traded asset units
            slippage: Maximum acceptable slippage percentage (e.g., 0.01 = 1%)
        
        Returns:
            Order object with execution details
        
        Raises:
            ValueError: If slippage is None or invalid
        """
        pass
    
    @abstractmethod
    async def place_market_sell_order(self, symbol: str, size: float, slippage: float) -> Order:
        """
        Place a market sell order with explicit slippage protection.
        
        Args:
            symbol: Trading pair symbol
            size: Order size in traded asset units
            slippage: Maximum acceptable slippage percentage (e.g., 0.01 = 1%)
        
        Returns:
            Order object with execution details
        
        Raises:
            ValueError: If slippage is None or invalid
        """
        pass
    
    @abstractmethod
    async def close_buy_position(self, symbol: str, size: float, slippage: Optional[float] = None) -> Order:
        """
        Close a long position.
        
        Args:
            symbol: Trading pair symbol
            size: Amount to close in traded asset units
            slippage: Maximum acceptable slippage percentage (e.g., 0.01 = 1%) - optional
        
        Returns:
            Order object with execution details
        """
        pass
    
    @abstractmethod
    async def close_sell_position(self, symbol: str, size: float, slippage: Optional[float] = None) -> Order:
        """
        Close a short position.
        
        Args:
            symbol: Trading pair symbol
            size: Amount to close in traded asset units
            slippage: Maximum acceptable slippage percentage (e.g., 0.01 = 1%) - optional
        
        Returns:
            Order object with execution details
        """
        pass
    
    @abstractmethod
    async def get_open_positions(self) -> List[Position]:
        pass
    
    

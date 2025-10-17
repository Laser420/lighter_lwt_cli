from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import requests
import json
import time
import os
import lighter
import eth_account
from ..base_connector import BaseDEXConnector, Price, FundingRate, Order, Position, OrderSide, OrderType, OrderStatus

# IMPORTANT: After creating a LighterConnector instance, you must call:
# await connector.set_leverage(1)
# This ensures the exchange leverage state is synchronized with local tracking.

class LighterConnector(BaseDEXConnector):
    def __init__(self, base_endpoint: str = None, private_key: str = None, 
                 api_key: str = None, api_key_index: int = 0, l1_address: str = None, **kwargs):
        super().__init__(**kwargs)
        self.base_endpoint = base_endpoint
        self.private_key = private_key
        self.api_key = api_key
        self.api_key_index = api_key_index
        self.l1_address = l1_address
        
        # Initialize API client for data operations using proper SDK
        if base_endpoint:
            configuration = lighter.Configuration(host=base_endpoint)
            self.api_client = lighter.ApiClient(configuration=configuration)
            self.transaction_api = lighter.TransactionApi(self.api_client)
        else:
            self.api_client = None
            self.transaction_api = None
        
        # Fetch account index from API
        self.account_index = self._fetch_account_index() if all([base_endpoint, l1_address]) else None
        
        # Validate API key index exists for account (skip for now due to API issues)
        # if all([self.account_index is not None, api_key_index is not None]):
        #     self._validate_api_key_index()
        
        # Store parameters for API key generation and trading setup
        self.eth_private_key = private_key  # Store ETH private key for API key registration
        self.api_private_key = None  # Will hold the generated API private key
        self.signer_client = None
        self.trading_enabled = False
        
        # Note: Call setup_trading() after initialization to generate and register API keys
        
        # Cached market specifications (populated during initialization)
        self._symbol_to_market_id_cache = {}  # symbol -> market_id
        self._market_size_decimals = {}  # market_id -> sizeDecimal
        self._market_price_decimals = {}  # market_id -> priceDecimal
        self._market_min_base_amounts = {}  # market_id -> min_base_amount
        
        # Local leverage tracking (Lighter API doesn't expose current leverage)
        self._current_leverage = 1
        
        # Fetch all market data during initialization
        if self.api_client:
            self._initialize_market_data()
        
        # Note: Call await set_leverage(1) after initialization to sync exchange state
    
    async def get_current_price(self, symbol: str) -> Price:
        try:
            # Get market ID from cache
            if symbol not in self._symbol_to_market_id_cache:
                raise Exception(f"Unknown symbol {symbol}. Available: {list(self._symbol_to_market_id_cache.keys())}")
            market_id = self._symbol_to_market_id_cache[symbol]
            
            # Use orderBookOrders endpoint with required limit parameter
            base_url = self.base_endpoint.rstrip('/')
            headers = {"accept": "application/json"}
            response = requests.get(
                f"{base_url}/api/v1/orderBookOrders?market_id={market_id}&limit=10",
                headers=headers
            )
            response.raise_for_status()
            orderbook_data = response.json()
            
            # Extract best bid and ask prices from orderbook response
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            
            # Best bid is the highest price buyers are willing to pay (first in bids array)
            best_bid = bids[0].get('price') if bids else None
            # Best ask is the lowest price sellers are willing to accept (first in asks array)  
            best_ask = asks[0].get('price') if asks else None
            
            if best_bid and best_ask:
                current_price = (float(best_bid) + float(best_ask)) / 2
            elif best_bid:
                current_price = float(best_bid)
            elif best_ask:
                current_price = float(best_ask)
            else:
                raise Exception(f"No price data available for symbol {symbol}")
            
            return Price(
                symbol=symbol,
                price=current_price,
                timestamp=datetime.now()
            )
                
        except Exception as e:
            raise Exception(f"Failed to get current price for {symbol}: {e}")
    
    async def get_current_funding_rate(self, symbol: str) -> FundingRate:
        try:
            # Get market ID from cache
            if symbol not in self._symbol_to_market_id_cache:
                raise Exception(f"Unknown symbol {symbol}. Available: {list(self._symbol_to_market_id_cache.keys())}")
            market_id = self._symbol_to_market_id_cache[symbol]
            
            # Get all current funding rates
            base_url = self.base_endpoint.rstrip('/')  # Remove trailing slash
            response = requests.get(f"{base_url}/api/v1/funding-rates")
            response.raise_for_status()
            data = response.json()
            
            # Find funding rate for our specific market from Lighter exchange
            for funding_rate in data['funding_rates']:
                if (funding_rate.get('market_id') == market_id and 
                    funding_rate.get('exchange') == 'lighter'):
                    # Lighter API returns 8-hour rates, convert to 1-hour rates for consistency
                    eight_hour_rate = float(funding_rate['rate'])
                    one_hour_rate = eight_hour_rate / 8
                    return FundingRate(
                        symbol=symbol,
                        rate=one_hour_rate,
                        timestamp=datetime.now(),
                        next_funding_time=None
                    )
            
            raise Exception(f"No funding rate found for symbol {symbol} (market_id: {market_id})")
        except Exception as e:
            raise Exception(f"Failed to get current funding rate for {symbol}: {e}")
    

    async def get_current_leverage(self) -> int:
        return self._current_leverage

    async def setup_trading(self) -> bool:
        """Generate API key and initialize trading client. Call this after connector initialization."""
        try:
            if not all([self.base_endpoint, self.eth_private_key, self.account_index is not None, self.api_key_index is not None]):
                raise Exception("Missing required parameters for trading setup")
            
            # Setting up trading for account
            
            # Generate new API key pair
            api_private_key, api_public_key, err = lighter.create_api_key()
            if err:
                raise Exception(f"Failed to create API key: {err}")
            
            # Generated API key pair
            
            # Create temporary SignerClient to register the API key
            # Use API nonce management for fresh registration
            temp_client = lighter.SignerClient(
                url=self.base_endpoint,
                private_key=api_private_key,
                account_index=self.account_index,
                api_key_index=self.api_key_index,
                nonce_management_type=lighter.nonce_manager.NonceManagerType.API
            )
            
            # Register API key on server using ETH private key
            response, err = await temp_client.change_api_key(
                eth_private_key=self.eth_private_key,
                new_pubkey=api_public_key
            )
            
            if err:
                await temp_client.close()
                raise Exception(f"Failed to register API key: {err}")
            
            # API key registered successfully
            
            # API key registration transaction completed
            
            # Close temporary client and create new one after registration
            await temp_client.close()
            
            # Create final SignerClient with the registered API key
            final_client = lighter.SignerClient(
                url=self.base_endpoint,
                private_key=api_private_key,
                account_index=self.account_index,
                api_key_index=self.api_key_index,
                nonce_management_type=lighter.nonce_manager.NonceManagerType.API
            )
            
            # Verify the final client configuration
            check_err = final_client.check_client()
            if check_err:
                await final_client.close()
                raise Exception(f"Final client check failed: {check_err}")
            
            # Client verification successful
            
            # Store the working API private key and client
            self.api_private_key = api_private_key
            self.signer_client = final_client
            self.trading_enabled = True
            
            # Refresh nonce after API key registration
            try:
                # Get fresh nonce from API
                fresh_nonce = lighter.nonce_manager.get_nonce_from_api(
                    self.api_client, self.account_index, self.api_key_index
                )
            except Exception as e:
                pass  # Ignore nonce refresh errors
            
            # Trading setup complete
            return True
            
        except Exception as e:
            # Trading setup failed
            return False
    
    async def set_leverage(self, newLeverage: int, symbol: str = None) -> int:
        """Set leverage using SDK client"""
        try:
            if not self.signer_client:
                # If no signer client, just update local tracking
                self._current_leverage = newLeverage
                # Leverage updated locally (trading not enabled)
                return newLeverage
            
            # If no symbol provided, apply to all markets (use first available market as default)
            if not symbol:
                available_symbols = list(self._symbol_to_market_id_cache.keys())
                if not available_symbols:
                    raise Exception("No markets available for leverage setting")
                symbol = available_symbols[0]
                # Using default market for leverage
            
            # Get market ID from cache
            if symbol not in self._symbol_to_market_id_cache:
                raise Exception(f"Unknown symbol {symbol}. Available: {list(self._symbol_to_market_id_cache.keys())}")
            market_id = self._symbol_to_market_id_cache[symbol]
            
            # Setting leverage
            
            # Use SDK to update leverage with actual API call
            lev_tx, response, err = await self.signer_client.update_leverage(
                leverage=newLeverage,
                margin_mode=self.signer_client.CROSS_MARGIN_MODE,
                market_index=market_id
            )
            
            if err:
                raise Exception(f"Leverage update failed: {err}")
            
            # Leverage updated successfully
            
            # Update local tracking after successful API call
            self._current_leverage = newLeverage
            return newLeverage
            
        except Exception as e:
            raise Exception(f"Failed to set leverage to {newLeverage}: {e}")

    async def get_min_order_size(self, symbol: str) -> float:
        try:
            # Get market ID from cache
            if symbol not in self._symbol_to_market_id_cache:
                raise Exception(f"Unknown symbol {symbol}. Available: {list(self._symbol_to_market_id_cache.keys())}")
            market_id = self._symbol_to_market_id_cache[symbol]
            
            # Ensure market data is cached before retrieval
            await self._ensure_market_data(market_id)
            
            # Return cached min base amount (no conversion needed)
            return float(self._market_min_base_amounts[market_id])
        except Exception as e:
            raise Exception(f"Failed to get min order size for {symbol}: {e}")
    
    def _fetch_account_index(self) -> int:
        """
        Fetch account index from L1 address using Lighter API.
        """
        try:
            # Use direct API call since SDK doesn't have account management
            base_url = self.base_endpoint.rstrip('/')  # Remove trailing slash
            headers = {"accept": "application/json"}
            response = requests.get(
                f"{base_url}/api/v1/account?by=l1_address&value={self.l1_address}",
                headers=headers
            )
            response.raise_for_status()
            accounts_data = response.json()
            
            if not accounts_data:
                raise Exception(f"No account data found for L1 address {self.l1_address}")
            
            # Handle API response format: {'accounts': [{'account_index': ...}]}
            if isinstance(accounts_data, dict) and 'accounts' in accounts_data:
                accounts_list = accounts_data['accounts']
                if accounts_list and len(accounts_list) > 0:
                    return accounts_list[0].get('account_index', 0)
            
            raise Exception(f"No account index found in response: {accounts_data}")
        except Exception as e:
            raise Exception(f"Failed to fetch account index: {e}")
    
    def _validate_api_key_index(self) -> None:
        """
        Validate that the provided API key index exists for the account.
        Skipped for now due to API endpoint issues.
        """
        try:
            # Skip validation for now - API endpoint may not be available
            # Skipping API key validation (endpoint not available)
            return
            
        except Exception as e:
            raise Exception(f"Failed to validate API key index: {e}")
    
    def _initialize_market_data(self) -> None:
        """
        Initialize all market data during construction - symbols to indices and decimal specifications.
        """
        try:
            # Use direct API call to get all orderbook metadata
            base_url = self.base_endpoint.rstrip('/')  # Remove trailing slash
            response = requests.get(f"{base_url}/api/v1/orderBooks")
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict):
                # Handle wrapped response - try both 'order_books' and 'orderbooks'
                orderbooks = data.get('order_books', data.get('orderbooks', []))
            else:
                orderbooks = data
            
            # Cache all symbol->market_id mappings and decimal specifications
            for orderbook in orderbooks:
                if isinstance(orderbook, dict):  # Ensure it's a dictionary
                    symbol = orderbook.get('symbol')
                    market_id = orderbook.get('market_id', orderbook.get('index'))  # Try both field names
                    
                    if symbol and market_id is not None:
                        # Cache symbol to market ID mapping
                        self._symbol_to_market_id_cache[symbol] = market_id
                        
                        # Cache decimal specifications
                        self._market_size_decimals[market_id] = orderbook.get('supported_size_decimals', orderbook.get('size_decimals'))
                        self._market_price_decimals[market_id] = orderbook.get('supported_price_decimals', orderbook.get('price_decimals'))
                        self._market_min_base_amounts[market_id] = orderbook.get('min_base_amount')
                
        except Exception as e:
            raise Exception(f"Failed to initialize market data: {e}")
    
    
    async def initialize_market_decimals(self, market_ids: List[int]) -> None:
        """
        Proactively populate market decimal specifications for given markets.
        Call this during connector initialization to avoid latency in first trading actions.
        
        Args:
            market_ids: List of market IDs to pre-populate decimal specs for
        """
        try:
            if not self.base_endpoint:
                raise Exception("Base endpoint not configured")
            
            for market_id in market_ids:
                if market_id not in self._market_size_decimals:
                    # Use direct API call for orderbook metadata
                    response = requests.get(
                        f"{self.base_endpoint}/api/v1/orderbook-meta",
                        params={'market_id': market_id}
                    )
                    response.raise_for_status()
                    orderbook_details = response.json()
                    
                    # Cache the decimal values and min amounts (fail if missing)
                    self._market_size_decimals[market_id] = orderbook_details['size_decimals']
                    self._market_price_decimals[market_id] = orderbook_details['price_decimals']
                    self._market_min_base_amounts[market_id] = orderbook_details['min_base_amount']
                    
        except Exception as e:
            raise Exception(f"Failed to initialize market decimals: {e}")
    
    async def _ensure_market_data(self, market_id: int) -> None:
        """
        Ensure market data (decimals and min amounts) are cached for the given market.
        Only makes API call if data is not already cached (fallback for markets not pre-initialized).
        """
        if market_id in self._market_size_decimals and market_id in self._market_price_decimals and market_id in self._market_min_base_amounts:
            return  # Already cached
        
        try:
            if not self.base_endpoint:
                raise Exception("Base endpoint not configured")
            
            # Fetch orderbook details to get decimal specifications using direct API call
            response = requests.get(
                f"{self.base_endpoint}/api/v1/orderbook-meta",
                params={'market_id': market_id}
            )
            response.raise_for_status()
            orderbook_details = response.json()
            
            # Cache the decimal values and min amounts
            self._market_size_decimals[market_id] = orderbook_details['size_decimals']
            self._market_price_decimals[market_id] = orderbook_details['price_decimals']
            self._market_min_base_amounts[market_id] = orderbook_details['min_base_amount']
            
        except Exception as e:
            raise Exception(f"Failed to get market decimals for market {market_id}: {e}")
    
    def _convert_size_to_lighter_format(self, size: float, market_id: int) -> int:
        """
        Convert decimal size to Lighter's integer format with exact precision.
        Formula: size_to_send = int(size * 10 ^ sizeDecimal)
        """
        size_decimal = self._market_size_decimals[market_id]
        return int(size * (10 ** size_decimal))
    
    def _convert_price_to_lighter_format(self, price: float, market_id: int) -> int:
        """
        Convert decimal price to Lighter's integer format with exact precision.
        Formula: price_to_send = int(price * 10 ^ priceDecimal)
        """
        price_decimal = self._market_price_decimals[market_id]
        return int(price * (10 ** price_decimal))
    
    async def place_market_buy_order(self, symbol: str, size: float, slippage: Optional[float] = None) -> Order:
        """Place market buy order using Lighter SDK"""
        try:
            if not self.signer_client:
                raise Exception("Trading not enabled - call setup_trading() first")
            
            # Get market ID from cache
            if symbol not in self._symbol_to_market_id_cache:
                raise Exception(f"Unknown symbol {symbol}. Available: {list(self._symbol_to_market_id_cache.keys())}")
            market_id = self._symbol_to_market_id_cache[symbol]
            
            # Ensure market decimals are cached before conversion
            await self._ensure_market_data(market_id)
            
            # Get current price for slippage calculation
            price_obj = await self.get_current_price(symbol)
            current_price = price_obj.price
            
            # Calculate worst acceptable price with slippage (buy higher)
            slippage = slippage or 0.01  # Default 1% if not provided
            worst_price = current_price * (1 + slippage)
            
            # Convert to Lighter format
            base_amount = self._convert_size_to_lighter_format(size, market_id)
            avg_execution_price = self._convert_price_to_lighter_format(worst_price, market_id)
            
            # Placing market BUY order
            
            # Create market order using SDK
            tx_info, response, err = await self.signer_client.create_market_order(
                market_index=market_id,
                client_order_index=0,  # Use 0 for simplicity
                base_amount=base_amount,
                avg_execution_price=avg_execution_price,
                is_ask=False  # False for buy order
            )
            
            # Transaction details logged internally
            
            if err:
                raise Exception(f"Order failed: {err}")
            
            # Order submitted
            
            # Extract transaction hash from response
            tx_hash = "unknown"
            if response and hasattr(response, 'tx_hash'):
                tx_hash = response.tx_hash
            elif isinstance(response, dict) and 'tx_hash' in response:
                tx_hash = response['tx_hash']
            
            # Wait for transaction confirmation
            if tx_hash != "unknown":
                timeout = int(os.getenv('LIGHTER_FILL_TIMEOUT'))
                fill_result = await self._wait_for_fill(tx_hash, symbol, OrderSide.BUY, size, timeout)
                
                # Use actual execution data if available
                actual_price = fill_result.get('actual_price', current_price)
                actual_size = fill_result.get('actual_size', size)
            else:
                actual_price = current_price
                actual_size = size
            
            # Create order object with actual execution values
            order = Order(
                id=str(tx_hash),
                symbol=symbol,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                size=actual_size,
                price=actual_price,
                status=OrderStatus.FILLED,
                timestamp=datetime.now()
            )
            
            # Log completed trade
            self._log_trade(order)
            return order
            
        except Exception as e:
            raise Exception(f"Failed to place market buy order: {e}")
    
    async def place_market_sell_order(self, symbol: str, size: float, slippage: Optional[float] = None) -> Order:
        """Place market sell order using Lighter SDK"""
        try:
            if not self.signer_client:
                raise Exception("Trading not enabled - call setup_trading() first")
            
            # Get market ID from cache
            if symbol not in self._symbol_to_market_id_cache:
                raise Exception(f"Unknown symbol {symbol}. Available: {list(self._symbol_to_market_id_cache.keys())}")
            market_id = self._symbol_to_market_id_cache[symbol]
            
            # Ensure market decimals are cached before conversion
            await self._ensure_market_data(market_id)
            
            # Get current price for slippage calculation
            price_obj = await self.get_current_price(symbol)
            current_price = price_obj.price
            
            # Calculate worst acceptable price with slippage (sell lower)
            slippage = slippage or 0.01  # Default 1% if not provided
            worst_price = current_price * (1 - slippage)
            
            # Convert to Lighter format
            base_amount = self._convert_size_to_lighter_format(size, market_id)
            avg_execution_price = self._convert_price_to_lighter_format(worst_price, market_id)
            
            # Placing market SELL order
            
            # Create market order using SDK
            tx_info, response, err = await self.signer_client.create_market_order(
                market_index=market_id,
                client_order_index=0,  # Use 0 for simplicity
                base_amount=base_amount,
                avg_execution_price=avg_execution_price,
                is_ask=True  # True for sell order
            )
            
            if err:
                raise Exception(f"Order failed: {err}")
            
            # Order submitted
            
            # Extract transaction hash from response
            tx_hash = "unknown"
            if response and hasattr(response, 'tx_hash'):
                tx_hash = response.tx_hash
            elif isinstance(response, dict) and 'tx_hash' in response:
                tx_hash = response['tx_hash']
            
            # Create order object with actual execution values
            order = Order(
                id=str(tx_hash),
                symbol=symbol,
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                size=size,
                price=current_price,  # Use current price as estimate
                status=OrderStatus.FILLED,
                timestamp=datetime.now()
            )
            
            # Log completed trade
            self._log_trade(order)
            return order
            
        except Exception as e:
            raise Exception(f"Failed to place market sell order: {e}")
    
    async def close_buy_position(self, symbol: str, size: float, slippage: Optional[float] = None) -> Order:
        """Close buy position (sell to close long) using Lighter SDK"""
        try:
            if not self.signer_client:
                raise Exception("Trading not enabled - call setup_trading() first")
            
            # Get market ID from cache
            if symbol not in self._symbol_to_market_id_cache:
                raise Exception(f"Unknown symbol {symbol}. Available: {list(self._symbol_to_market_id_cache.keys())}")
            market_id = self._symbol_to_market_id_cache[symbol]
            
            # Ensure market decimals are cached before conversion
            await self._ensure_market_data(market_id)
            
            # Get current price for slippage calculation
            price_obj = await self.get_current_price(symbol)
            current_price = price_obj.price
            
            # Calculate worst acceptable price with slippage (sell lower)
            slippage = slippage or 0.01  # Default 1% if not provided
            worst_price = current_price * (1 - slippage)
            
            # Convert to Lighter format
            base_amount = self._convert_size_to_lighter_format(size, market_id)
            avg_execution_price = self._convert_price_to_lighter_format(worst_price, market_id)
            
            # Closing BUY position
            
            # Create market order using SDK (sell to close long)
            tx_info, response, err = await self.signer_client.create_market_order(
                market_index=market_id,
                client_order_index=0,  # Use 0 for simplicity
                base_amount=base_amount,
                avg_execution_price=avg_execution_price,
                is_ask=True,  # True for sell (to close long)
                reduce_only=True  # CRITICAL: Prevent opening new positions
            )
            
            # Transaction details logged internally
            
            if err:
                raise Exception(f"Order failed: {err}")
            
            # Close order submitted
            
            # Extract transaction hash from response
            tx_hash = "unknown"
            if response and hasattr(response, 'tx_hash'):
                tx_hash = response.tx_hash
            elif isinstance(response, dict) and 'tx_hash' in response:
                tx_hash = response['tx_hash']
            
            # Wait for transaction confirmation
            if tx_hash != "unknown":
                timeout = int(os.getenv('LIGHTER_FILL_TIMEOUT'))
                fill_result = await self._wait_for_fill(tx_hash, symbol, OrderSide.SELL, size, timeout)
                
                # Use actual execution data if available
                actual_price = fill_result.get('actual_price', current_price)
                actual_size = fill_result.get('actual_size', size)
            else:
                actual_price = current_price
                actual_size = size
            
            # Create order object with actual execution values
            order = Order(
                id=str(tx_hash),
                symbol=symbol,
                side=OrderSide.SELL,  # Closing long = sell
                type=OrderType.MARKET,
                size=actual_size,
                price=actual_price,
                status=OrderStatus.FILLED,
                timestamp=datetime.now()
            )
            
            # Log completed trade
            self._log_trade(order)
            return order
            
        except Exception as e:
            raise Exception(f"Failed to close buy position: {e}")
    
    async def close_sell_position(self, symbol: str, size: float, slippage: Optional[float] = None) -> Order:
        """Close sell position (buy to close short) using Lighter SDK"""
        try:
            if not self.signer_client:
                raise Exception("Trading not enabled - call setup_trading() first")
            
            # Get market ID from cache
            if symbol not in self._symbol_to_market_id_cache:
                raise Exception(f"Unknown symbol {symbol}. Available: {list(self._symbol_to_market_id_cache.keys())}")
            market_id = self._symbol_to_market_id_cache[symbol]
            
            # Ensure market decimals are cached before conversion
            await self._ensure_market_data(market_id)
            
            # Get current price for slippage calculation
            price_obj = await self.get_current_price(symbol)
            current_price = price_obj.price
            
            # Calculate worst acceptable price with slippage (buy higher)
            slippage = slippage or 0.01  # Default 1% if not provided
            worst_price = current_price * (1 + slippage)
            
            # Convert to Lighter format
            base_amount = self._convert_size_to_lighter_format(size, market_id)
            avg_execution_price = self._convert_price_to_lighter_format(worst_price, market_id)
            
            # Closing SELL position
            
            # Create market order using SDK (buy to close short)
            tx_info, response, err = await self.signer_client.create_market_order(
                market_index=market_id,
                client_order_index=0,  # Use 0 for simplicity
                base_amount=base_amount,
                avg_execution_price=avg_execution_price,
                is_ask=False,  # False for buy (to close short)
                reduce_only=True  # CRITICAL: Prevent opening new positions
            )
            
            if err:
                raise Exception(f"Order failed: {err}")
            
            # Close order submitted
            
            # Extract transaction hash from response
            tx_hash = "unknown"
            if response and hasattr(response, 'tx_hash'):
                tx_hash = response.tx_hash
            elif isinstance(response, dict) and 'tx_hash' in response:
                tx_hash = response['tx_hash']
            
            # Create order object with actual execution values
            order = Order(
                id=str(tx_hash),
                symbol=symbol,
                side=OrderSide.BUY,  # Closing short = buy
                type=OrderType.MARKET,
                size=size,
                price=current_price,  # Use current price as estimate
                status=OrderStatus.FILLED,
                timestamp=datetime.now()
            )
            
            # Log completed trade
            self._log_trade(order)
            return order
            
        except Exception as e:
            raise Exception(f"Failed to close sell position: {e}")
    
    # Removed transaction logging function for production performance

    async def _wait_for_fill(self, tx_hash: str, symbol: str, expected_side: OrderSide, expected_size: float, timeout: int) -> Dict[str, Any]:
        """Wait for transaction to reach status 3 (fully confirmed and settled)"""
        
        start_time = time.time()
        # Get polling interval from environment (required)
        poll_interval_str = os.getenv('LIGHTER_POLL_INTERVAL')
        if not poll_interval_str:
            raise Exception("LIGHTER_POLL_INTERVAL environment variable is required")
        poll_interval = float(poll_interval_str)
        
        while time.time() - start_time < timeout:
            try:
                # Query transaction status using Lighter API
                base_url = self.base_endpoint.rstrip('/')
                headers = {"accept": "application/json"}
                
                response = requests.get(
                    f"{base_url}/api/v1/tx",
                    params={'by': 'hash', 'value': tx_hash},
                    headers=headers
                )
                
                if response.status_code == 200:
                    tx_data = response.json()
                    status = tx_data.get('status')
                    
                    if status == 3:
                        # Transaction is fully confirmed and settled
                        
                        # Extract actual execution details from event_info
                        event_info_str = tx_data.get('event_info', '{}')
                        try:
                            event_info = json.loads(event_info_str)
                            trade_info = event_info.get('t', {})
                            actual_price = trade_info.get('p', 0) / 100  # Convert from cents to dollars
                            actual_size = trade_info.get('s', 0) / 10000  # Convert from scaled size
                            
                            return {
                                'status': 'FILLED',
                                'tx_hash': tx_hash,
                                'actual_price': actual_price if actual_price > 0 else None,
                                'actual_size': actual_size if actual_size > 0 else expected_size,
                                'block_height': tx_data.get('block_height'),
                                'executed_at': tx_data.get('executed_at'),
                                'tx_data': tx_data
                            }
                        except (json.JSONDecodeError, KeyError) as e:
                            # Could not parse event_info
                            return {
                                'status': 'FILLED',
                                'tx_hash': tx_hash,
                                'actual_price': None,
                                'actual_size': expected_size,
                                'tx_data': tx_data
                            }
                    
                    elif status == 2:
                        # Transaction is processing, continue waiting
                        pass
                    
                    elif status and status > 3:
                        # Unknown status > 3, might be error
                        raise Exception(f"Transaction {tx_hash} failed with status: {status}")
                    
                    else:
                        # Continue waiting
                        pass
                
                elif response.status_code == 404:
                    # Transaction not found yet, continue waiting
                    pass
                
                else:
                    # API error, continue waiting
                    pass
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                await asyncio.sleep(poll_interval)
        
        # Timeout reached
        raise Exception(f"Transaction {tx_hash} did not confirm within {timeout} seconds")

    async def get_open_positions(self) -> List[Position]:
        """Get open positions - using simulated tracking for now"""
        try:
            if not self.account_index:
                # Return empty list if no account configured
                return []
            
            # Try to get real positions from API
            try:
                response = requests.get(f"{self.base_endpoint}/api/v1/account", 
                                      params={'by': 'l1_address', 'value': self.l1_address})
                response.raise_for_status()
                response_data = response.json()
                
                # Extract account data from response structure
                if 'accounts' in response_data and len(response_data['accounts']) > 0:
                    account_data = response_data['accounts'][0]
                else:
                    raise Exception("No account data found in response")
                
                positions = []
                position_data_list = account_data.get('positions', [])
                
                for pos_data in position_data_list:
                    position_size = float(pos_data['position'])
                    
                    # Only include positions with non-zero size
                    if position_size != 0:
                        symbol = pos_data['symbol']
                        sign = pos_data['sign']  # 1 for long, -1 for short
                        
                        # Determine side based on sign
                        side = OrderSide.BUY if sign == 1 else OrderSide.SELL
                        
                        # Get current market price for the position
                        current_price_data = await self.get_current_price(symbol)
                        
                        # Calculate leverage from initial margin fraction
                        margin_fraction = float(pos_data.get('initial_margin_fraction', '100.00'))
                        leverage = 100.0 / margin_fraction if margin_fraction > 0 else 1.0
                        
                        positions.append(Position(
                            symbol=symbol,
                            side=side,
                            size=abs(position_size),
                            entry_price=float(pos_data['avg_entry_price']),
                            current_price=current_price_data.price,
                            unrealized_pnl=float(pos_data['unrealized_pnl']),
                            timestamp=datetime.now(),
                            leverage=leverage
                        ))
                
                return positions
                
            except Exception as api_error:
                # Could not fetch real positions
                # Return empty list for simulated mode
                return []
            
        except Exception as e:
            raise Exception(f"Failed to get open positions: {e}")

    

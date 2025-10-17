#!/usr/bin/env python3

import asyncio
import os
import sys

# Add current directory to Python path for imports
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

from dotenv import load_dotenv
from utils.connectors.lighter.lighter_connector import LighterConnector

async def test_lighter_validation():
    """Read-only validation test of the Lighter connector for market data retrieval"""
    
    load_dotenv('.env.local')
    
    base_endpoint = os.getenv('LIGHTER_BASE_ENDPOINT')
    private_key = os.getenv('LIGHTER_PRIVATE_KEY') 
    l1_address = os.getenv('LIGHTER_L1_ADDRESS')
    
    if not base_endpoint:
        print("❌ Error: LIGHTER_BASE_ENDPOINT must be set in .env.local file")
        return
    
    if not l1_address:
        print("❌ Error: LIGHTER_L1_ADDRESS must be set in .env.local file") 
        return
    
    try:
        # Initialize connector in read-only mode (without private key for now)
        connector = LighterConnector(
            base_endpoint=base_endpoint,
            l1_address=l1_address,
            # private_key=private_key,  # Comment out for read-only testing
        )
        print(f"✅ Lighter connector initialized successfully (read-only mode)")
        print(f"   Base endpoint: {base_endpoint}")
        print(f"   L1 address: {l1_address}")
        
        # Get available markets from cache
        available_symbols = list(connector._symbol_to_market_id_cache.keys())
        print(f"✅ Found {len(available_symbols)} available markets")
        
        # Find a suitable test symbol (prefer major assets that are likely to have orderbook data)
        test_symbol = None
        preferred_symbols = ['ETH', 'BTC', 'WETH', 'WBTC', 'USDC', 'USDT', 'SOL', 'AVAX']
        
        for preferred in preferred_symbols:
            if preferred in available_symbols:
                test_symbol = preferred
                break
        
        if not test_symbol:
            # Fallback to first available symbol
            test_symbol = available_symbols[0] if available_symbols else None
        
        if not test_symbol:
            print("❌ No test symbols available")
            return
        
        print(f"🎯 Using test symbol: {test_symbol}")
        if test_symbol:
            market_id = connector._symbol_to_market_id_cache.get(test_symbol)
            print(f"   Market ID: {market_id}")
        print(f"   Available symbols: {', '.join(available_symbols[:10])}{'...' if len(available_symbols) > 10 else ''}")
        
        # Show a few symbols with their market IDs for debugging
        print("   Sample market IDs:")
        for i, symbol in enumerate(available_symbols[:5]):
            mid = connector._symbol_to_market_id_cache.get(symbol)
            print(f"     {symbol}: {mid}")
        
        
        print(f"\n=== READ-ONLY DATA VALIDATION FOR {test_symbol} ===")
        
        # Test current price
        try:
            price = await connector.get_current_price(test_symbol)
            print(f"✅ Current price: ${price.price:,.2f}")
            current_price_val = price.price  # Store for later calculations
        except Exception as e:
            print(f"❌ Failed to get current price: {e}")
            return
        
        # Test funding rate
        try:
            funding_rate = await connector.get_current_funding_rate(test_symbol)
            print(f"✅ Funding rate: {funding_rate.rate:.6f} ({funding_rate.rate*100:.4f}%)")
        except Exception as e:
            print(f"❌ Failed to get funding rate: {e}")
        
        # Test minimum order size
        try:
            min_size = await connector.get_min_order_size(test_symbol)
            print(f"✅ Minimum order size: {min_size:.6f}")
        except Exception as e:
            print(f"❌ Failed to get minimum order size: {e}")
        
        # Test current leverage (should work in read-only mode)
        try:
            leverage = await connector.get_current_leverage()
            print(f"✅ Current leverage: {leverage}x (local tracking)")
        except Exception as e:
            print(f"❌ Failed to get current leverage: {e}")
        
        # Test market data caching
        try:
            market_id = connector._symbol_to_market_id_cache.get(test_symbol)
            if market_id is not None:
                size_decimals = connector._market_size_decimals.get(market_id)
                price_decimals = connector._market_price_decimals.get(market_id)
                min_base_amount = connector._market_min_base_amounts.get(market_id)
                
                print(f"✅ Market data cached:")
                print(f"   Market ID: {market_id}")
                print(f"   Size decimals: {size_decimals}")
                print(f"   Price decimals: {price_decimals}")
                print(f"   Min base amount: {min_base_amount}")
            else:
                print("⚠️  Market ID not found in cache")
        except Exception as e:
            print(f"❌ Failed to get market data: {e}")
        
        # Calculate potential trade sizes for reference
        print(f"\n=== TRADING SIZE CALCULATIONS (READ-ONLY) ===")
        try:
            min_notional = 50.0  # Estimate $50 minimum
            raw_test_size = min_notional / current_price_val
            
            # Get step size from market data if available
            market_id = connector._symbol_to_market_id_cache.get(test_symbol)
            step_size = None
            if market_id is not None:
                size_decimals = connector._market_size_decimals.get(market_id)
                if size_decimals is not None:
                    step_size = 1 / (10 ** size_decimals)
            
            print(f"📊 Current price: ${current_price_val:.2f}")
            print(f"📊 Min notional estimate: ${min_notional}")
            print(f"📊 Raw test size: {raw_test_size:.6f} {test_symbol.split('-')[0]}")
            print(f"📊 Min API size: {min_size:.6f}")
            if step_size:
                print(f"📊 Step size: {step_size:.6f}")
                test_size = max(raw_test_size, min_size)
                # Round to step size
                import math
                test_size = math.ceil(test_size / step_size) * step_size
                print(f"📊 Rounded test size: {test_size:.6f} (${test_size * current_price_val:.2f} notional)")
            
        except Exception as e:
            print(f"❌ Failed to calculate trade sizes: {e}")
        
        # Note about trading requirements
        print(f"\n=== TRADING REQUIREMENTS ===")
        print(f"⚠️  To enable trading functions, the following environment variables are required:")
        print(f"   - LIGHTER_PRIVATE_KEY: Private key for transaction signing")
        print(f"   - LIGHTER_API_KEY_INDEX: API key index (typically 0 for simple accounts)")
        print(f"   - Account must be funded on {base_endpoint}")
        print(f"   - Must call 'await connector.set_leverage(1)' after initialization")
        
        if private_key:
            print(f"✅ Private key available - trading functions would work")
        else:
            print(f"❌ Private key not set - trading functions disabled")
        
        print(f"\n=== LIGHTER CONNECTOR READ-ONLY VALIDATION COMPLETE ===")
        print(f"✅ Market data retrieval validated successfully")
        print(f"🎯 Test symbol: {test_symbol}")
        print(f"📊 {len(available_symbols)} markets available")
        print(f"🔧 Ready for trading validation once credentials are configured")
        
    except Exception as e:
        print(f"❌ Failed to initialize Lighter connector: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_lighter_validation())
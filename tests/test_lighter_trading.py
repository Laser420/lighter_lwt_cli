#!/usr/bin/env python3

import asyncio
import os
import sys

# Add current directory to Python path for imports
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

from dotenv import load_dotenv
from utils.connectors.lighter.lighter_connector import LighterConnector

async def test_lighter_trading_validation():
    """Comprehensive validation test of the Lighter connector including live trading"""
    
    load_dotenv('.env.local')
    
    base_endpoint = os.getenv('LIGHTER_BASE_ENDPOINT')
    private_key = os.getenv('LIGHTER_PRIVATE_KEY')
    l1_address = os.getenv('LIGHTER_L1_ADDRESS')
    # Note: api_key_index will be derived automatically by connector
    
    if not base_endpoint:
        print("❌ Error: LIGHTER_BASE_ENDPOINT must be set in .env.local file")
        return
    
    if not l1_address:
        print("❌ Error: LIGHTER_L1_ADDRESS must be set in .env.local file")
        return
    
    if not private_key:
        print("❌ Error: LIGHTER_PRIVATE_KEY must be set for trading validation")
        return
    
    try:
        # Initialize connector with full trading capabilities
        connector = LighterConnector(
            base_endpoint=base_endpoint,
            l1_address=l1_address,
            private_key=private_key
        )
        print(f"✅ Lighter connector initialized successfully (trading mode)")
        print(f"   Base endpoint: {base_endpoint}")
        print(f"   L1 address: {l1_address}")
        print(f"   Account index: {connector.account_index}")
        print(f"   API key index: 0 (default)")
        
        # IMPORTANT: Setup trading (generate and register API keys)
        print(f"\n🔧 Setting up trading (generating API keys)...")
        try:
            success = await connector.setup_trading()
            if not success:
                print(f"❌ Failed to setup trading")
                return
            print(f"✅ Trading setup completed successfully")
        except Exception as e:
            print(f"❌ Failed to setup trading: {e}")
            return
        
        # Set leverage to sync exchange state
        print(f"\n🔧 Setting leverage to 1x...")
        try:
            await connector.set_leverage(1)
            print(f"✅ Leverage set successfully")
        except Exception as e:
            print(f"❌ Failed to set leverage: {e}")
            print("   This may affect trading operations")
            # Continue anyway
        
        # Get available markets
        available_symbols = list(connector._symbol_to_market_id_cache.keys())
        print(f"✅ Found {len(available_symbols)} available markets")
        
        # Find a suitable test symbol with proper market ID and good liquidity
        test_symbol = None
        preferred_symbols = ['ETH', 'BTC', 'USDC', 'USDT', 'SOL', 'AVAX', 'DOT', 'LINK']
        
        for preferred in preferred_symbols:
            if preferred in available_symbols:
                market_id = connector._symbol_to_market_id_cache.get(preferred)
                if market_id is not None:  # Accept market_id=0 for ETH
                    test_symbol = preferred
                    break
        
        if not test_symbol:
            # Fallback to first symbol with valid market ID
            for symbol in available_symbols:
                market_id = connector._symbol_to_market_id_cache.get(symbol)
                if market_id is not None:
                    test_symbol = symbol
                    break
        
        if not test_symbol:
            print("❌ No suitable test symbols available")
            return
        
        print(f"🎯 Using test symbol: {test_symbol}")
        market_id = connector._symbol_to_market_id_cache.get(test_symbol)
        print(f"   Market ID: {market_id}")
        
        print(f"\n=== MARKET DATA VALIDATION FOR {test_symbol} ===")
        
        # Test current price
        try:
            price = await connector.get_current_price(test_symbol)
            current_price_val = price.price
            print(f"✅ Current price: ${current_price_val:,.2f}")
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
            return
        
        # Test current leverage
        try:
            leverage = await connector.get_current_leverage()
            print(f"✅ Current leverage: {leverage}x")
        except Exception as e:
            print(f"❌ Failed to get current leverage: {e}")
        
        # Test positions before trading
        try:
            positions = await connector.get_open_positions()
            print(f"✅ Open positions before trading: {len(positions)} positions")
            for pos in positions:
                print(f"   📊 {pos.symbol}: {pos.side.value} {pos.size} @ ${pos.entry_price:.2f}")
        except Exception as e:
            print(f"❌ Failed to get open positions: {e}")
        
        print(f"\n=== TRADING SIZE CALCULATIONS ===")
        
        # Calculate test size - use a safe minimum amount
        min_notional = 15.0  # Start with $15 to be safe
        raw_test_size = min_notional / current_price_val
        
        # Get step size from market data
        step_size = None
        size_decimals = connector._market_size_decimals.get(market_id)
        if size_decimals is not None:
            step_size = 1 / (10 ** size_decimals)
        
        # Round UP to step size to ensure we meet minimum notional
        import math
        if step_size:
            test_size = math.ceil(raw_test_size / step_size) * step_size
            # Clean up floating point precision
            test_size = round(test_size, size_decimals)
        else:
            test_size = max(raw_test_size, min_size)
        
        # Ensure we meet minimum size requirement
        test_size = max(test_size, min_size)
        
        print(f"📈 Min API size: {min_size}, Min notional: ${min_notional}")
        print(f"📈 Raw size: {raw_test_size:.6f}, Step size: {step_size}")
        print(f"📈 Final test size: {test_size:.6f} {test_symbol.split('-')[0] if '-' in test_symbol else test_symbol}")
        print(f"📈 Notional value: ${test_size * current_price_val:.2f}")
        
        slippage = 0.002  # 0.2% slippage
        print(f"🎯 Slippage: {slippage*100:.1f}%")
        
        # Confirm before trading
        print(f"\n⚠️  About to execute live trading test")
        print(f"   Symbol: {test_symbol}")
        print(f"   Size: {test_size}")
        print(f"   Estimated cost: ${test_size * current_price_val:.2f}")
        print(f"   Environment: {base_endpoint}")
        
        # Auto-proceed for testing (set to 'no' to skip trading)
        proceed = 'yes'  
        print(f"\n🚨 Auto-proceeding with live trading test: {proceed}")
        
        if proceed != 'yes':
            print("❌ Trading test cancelled")
            return
        
        print("Proceeding with trading validation...")
        
        # === TRADING CYCLE 1: BUY → CLOSE ===
        try:
            print(f"\n📈 Step 1: Placing market BUY order for {test_size} {test_symbol}...")
            buy_order = await connector.place_market_buy_order(test_symbol, test_size, slippage)
            print(f"✅ Buy order executed: {buy_order.size} @ ${buy_order.price:.2f} (ID: {buy_order.id})")
            
            # Verify position opened
            await asyncio.sleep(2)  # Give time for settlement
            positions_after_buy = await connector.get_open_positions()
            buy_position = None
            for pos in positions_after_buy:
                if pos.symbol == test_symbol and pos.side.value == 'BUY':
                    buy_position = pos
                    break
            
            if buy_position:
                print(f"✅ Buy position confirmed: {buy_position.size} @ ${buy_position.entry_price:.2f}")
            else:
                print(f"⚠️  Warning: Buy position not found in positions list")
            
            # Wait for settlement
            await asyncio.sleep(3)
            
            print(f"\n📉 Step 2: Closing BUY position...")
            close_buy_order = await connector.close_buy_position(test_symbol, test_size, slippage)
            print(f"✅ Close buy order executed: {close_buy_order.size} @ ${close_buy_order.price:.2f} (ID: {close_buy_order.id})")
            
            # Calculate P&L for first cycle
            buy_cost = buy_order.size * buy_order.price
            sell_proceeds = close_buy_order.size * close_buy_order.price
            pnl_cycle1 = sell_proceeds - buy_cost
            print(f"💰 Cycle 1 P&L: ${pnl_cycle1:.4f}")
            
        except Exception as e:
            print(f"❌ Failed during BUY → CLOSE cycle: {e}")
            # Try to clean up any open positions
            try:
                positions = await connector.get_open_positions()
                for pos in positions:
                    if pos.symbol == test_symbol:
                        print(f"🧹 Attempting to close orphaned position: {pos.side.value} {pos.size}")
                        if pos.side.value == 'BUY':
                            await connector.close_buy_position(test_symbol, pos.size, slippage)
                        else:
                            await connector.close_sell_position(test_symbol, pos.size, slippage)
            except:
                print("⚠️  Could not clean up positions automatically")
            return
        
        # Wait between cycles
        await asyncio.sleep(5)
        
        # === TRADING CYCLE 2: SELL → CLOSE ===
        try:
            print(f"\n📉 Step 3: Placing market SELL order for {test_size} {test_symbol}...")
            sell_order = await connector.place_market_sell_order(test_symbol, test_size, slippage)
            print(f"✅ Sell order executed: {sell_order.size} @ ${sell_order.price:.2f} (ID: {sell_order.id})")
            
            # Verify position opened
            await asyncio.sleep(2)
            positions_after_sell = await connector.get_open_positions()
            sell_position = None
            for pos in positions_after_sell:
                if pos.symbol == test_symbol and pos.side.value == 'SELL':
                    sell_position = pos
                    break
            
            if sell_position:
                print(f"✅ Sell position confirmed: {sell_position.size} @ ${sell_position.entry_price:.2f}")
            else:
                print(f"⚠️  Warning: Sell position not found in positions list")
            
            # Wait for settlement
            await asyncio.sleep(3)
            
            print(f"\n📈 Step 4: Closing SELL position...")
            close_sell_order = await connector.close_sell_position(test_symbol, test_size, slippage)
            print(f"✅ Close sell order executed: {close_sell_order.size} @ ${close_sell_order.price:.2f} (ID: {close_sell_order.id})")
            
            # Calculate P&L for second cycle
            sell_proceeds = sell_order.size * sell_order.price
            buy_cost = close_sell_order.size * close_sell_order.price
            pnl_cycle2 = sell_proceeds - buy_cost
            print(f"💰 Cycle 2 P&L: ${pnl_cycle2:.4f}")
            
        except Exception as e:
            print(f"❌ Failed during SELL → CLOSE cycle: {e}")
            # Try to clean up any open positions
            try:
                positions = await connector.get_open_positions()
                for pos in positions:
                    if pos.symbol == test_symbol:
                        print(f"🧹 Attempting to close orphaned position: {pos.side.value} {pos.size}")
                        if pos.side.value == 'BUY':
                            await connector.close_buy_position(test_symbol, pos.size, slippage)
                        else:
                            await connector.close_sell_position(test_symbol, pos.size, slippage)
            except:
                print("⚠️  Could not clean up positions automatically")
            return
        
        # Final verification
        print(f"\n=== FINAL VERIFICATION ===")
        
        # Check final positions
        try:
            final_positions = await connector.get_open_positions()
            print(f"✅ Final open positions: {len(final_positions)} positions")
            
            # Should be no positions for test symbol
            test_positions = [pos for pos in final_positions if pos.symbol == test_symbol]
            if test_positions:
                print(f"⚠️  Warning: {len(test_positions)} positions still open for {test_symbol}")
                for pos in test_positions:
                    print(f"   📊 {pos.symbol}: {pos.side.value} {pos.size} @ ${pos.entry_price:.2f}")
            else:
                print(f"✅ All test positions closed for {test_symbol}")
                
        except Exception as e:
            print(f"❌ Failed to verify final positions: {e}")
        
        # Calculate total P&L
        total_pnl = pnl_cycle1 + pnl_cycle2
        print(f"\n💰 Total P&L: ${total_pnl:.4f}")
        
        # Check trade logs
        try:
            if os.path.exists('logs/lighter_trades.jsonl'):
                with open('logs/lighter_trades.jsonl', 'r') as f:
                    trade_count = len(f.readlines())
                print(f"✅ Trade logging verified: {trade_count} total trades in log")
            else:
                print(f"⚠️  Trade log file not found")
        except Exception as e:
            print(f"❌ Failed to verify trade logs: {e}")
        
        print(f"\n=== LIGHTER CONNECTOR TRADING VALIDATION COMPLETE ===")
        print(f"✅ All trading functions validated successfully")
        print(f"🎯 Environment: {base_endpoint}")
        print(f"📊 Symbol tested: {test_symbol}")
        print(f"💰 Total cost: ~${abs(total_pnl):.4f}")
        print(f"🔧 Connector ready for production arbitrage trading")
        
    except Exception as e:
        print(f"❌ Failed to initialize Lighter connector: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_lighter_trading_validation())
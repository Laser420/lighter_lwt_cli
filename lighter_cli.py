#!/usr/bin/env python3
"""
Lightweight Lighter CLI
Simple interactive trading commands for Lighter DEX
"""

import asyncio
import os
import sys
import logging
from typing import Optional
from dotenv import load_dotenv

from utils.connectors.lighter.lighter_connector import LighterConnector

# Disable debug logging from external libraries
import warnings
warnings.filterwarnings("ignore")

# Set logging levels to suppress debug output
logging.basicConfig(level=logging.ERROR, format='')
for logger_name in ['urllib3', 'urllib3.connectionpool', 'lighter', 'asyncio', 'requests', 'aiohttp', 'root']:
    logging.getLogger(logger_name).setLevel(logging.ERROR)
    logging.getLogger(logger_name).disabled = True

def create_connector() -> Optional[LighterConnector]:
    """Create and return a Lighter connector"""
    base_endpoint = os.getenv('LIGHTER_BASE_ENDPOINT')
    private_key = os.getenv('LIGHTER_PRIVATE_KEY')
    l1_address = os.getenv('LIGHTER_L1_ADDRESS')
    
    if not all([base_endpoint, private_key, l1_address]):
        print("❌ Error: Missing required environment variables in .env.local:")
        print("  LIGHTER_BASE_ENDPOINT")
        print("  LIGHTER_PRIVATE_KEY") 
        print("  LIGHTER_L1_ADDRESS")
        return None
    
    try:
        return LighterConnector(
            base_endpoint=base_endpoint,
            private_key=private_key,
            l1_address=l1_address
        )
    except Exception as e:
        print(f"❌ Error creating connector: {e}")
        return None

def get_user_input(prompt: str, input_type: str = "string") -> Optional[str]:
    """Get user input with validation"""
    try:
        value = input(f"{prompt}: ").strip()
        if not value:
            print("❌ Input cannot be empty")
            return None
        
        if input_type == "float":
            float(value)  # Validate it's a number
        elif input_type == "symbol":
            value = value.upper()  # Normalize symbol to uppercase
            
        return value
    except ValueError:
        print(f"❌ Invalid {input_type}")
        return None
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        return None

async def market_open_command(connector: LighterConnector):
    """Interactive market open command"""
    print("\n🔓 MARKET OPEN")
    print("=" * 40)
    
    # Get parameters from user
    symbol = get_user_input("Enter symbol (e.g. ETH)", "symbol")
    if not symbol:
        return
    
    side = get_user_input("Enter side (buy/sell)", "string")
    if not side or side.lower() not in ['buy', 'sell']:
        print("❌ Side must be 'buy' or 'sell'")
        return
    
    size = get_user_input("Enter size (in base asset)", "float")
    if not size:
        return
    
    slippage = get_user_input("Enter slippage % (e.g. 0.5 for 0.5%)", "float")
    if not slippage:
        return
    
    leverage = get_user_input("Enter leverage (default: 1)", "float")
    if not leverage:
        leverage = "1"  # Default to 1x leverage
    
    try:
        size_val = float(size)
        slippage_val = float(slippage) / 100  # Convert percentage to decimal
        leverage_val = float(leverage)
        
        print(f"\n📋 Order Summary:")
        print(f"   Symbol: {symbol}")
        print(f"   Side: {side.upper()}")
        print(f"   Size: {size_val}")
        print(f"   Leverage: {leverage_val}x")
        print(f"   Slippage: {slippage_val*100:.1f}%")
        
        # Get current price for confirmation
        try:
            price_info = await connector.get_current_price(symbol)
            estimated_usd = size_val * price_info.price
            print(f"   Current Price: ${price_info.price:,.2f}")
            print(f"   Estimated USD Cost: ${estimated_usd:,.2f}")
        except Exception as e:
            print(f"⚠️  Could not get current price: {e}")
        
        confirm = input("\n⚠️  Proceed with order? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Order cancelled")
            return
        
        print("\n🔄 Placing order...")
        
        # Set leverage before placing order
        await connector.set_leverage(int(leverage_val), symbol)
        print(f"✅ Leverage set to {leverage_val}x for {symbol}")
        
        if side.lower() == 'buy':
            order = await connector.place_market_buy_order(symbol, size_val, slippage_val)
        else:
            order = await connector.place_market_sell_order(symbol, size_val, slippage_val)
        
        print(f"✅ Order executed successfully!")
        print(f"   Order ID: {order.id}")
        print(f"   Size: {order.size}")
        print(f"   Price: ${order.price:.2f}")
        print(f"   Side: {order.side.value.upper()}")
        print(f"   Total: ${order.size * order.price:.2f}")
        
    except Exception as e:
        print(f"❌ Order failed: {e}")

async def market_close_command(connector: LighterConnector):
    """Interactive market close command"""
    print("\n🔒 MARKET CLOSE")
    print("=" * 40)
    
    # First, show current positions
    try:
        positions = await connector.get_open_positions()
        if not positions:
            print("❌ No open positions to close")
            return
        
        print("📊 Current Positions:")
        for i, pos in enumerate(positions):
            side_str = "LONG" if pos.side.value == "buy" else "SHORT"
            pnl_str = f"${pos.unrealized_pnl:+.2f}" if pos.unrealized_pnl != 0 else "$0.00"
            leverage_str = f"{pos.leverage:.1f}x" if hasattr(pos, 'leverage') else "1.0x"
            print(f"   {i+1}. {pos.symbol}: {side_str} {pos.size} @ ${pos.entry_price:.2f} ({leverage_str}, PnL: {pnl_str})")
        
        # Get user selection
        pos_num = get_user_input(f"\nSelect position to close (1-{len(positions)})", "string")
        if not pos_num:
            return
        
        # Check if input contains only digits (prevent accidental number input)
        if not pos_num.isdigit():
            print("❌ Please enter a valid position number (digits only)")
            return
        
        try:
            pos_index = int(pos_num) - 1
            if pos_index < 0 or pos_index >= len(positions):
                print("❌ Invalid position number")
                return
        except ValueError:
            print("❌ Invalid position number")
            return
        
        selected_pos = positions[pos_index]
        
        # Ask for size to close
        print(f"\nClosing {selected_pos.symbol} position:")
        print(f"   Current size: {selected_pos.size}")
        
        size_input = get_user_input(f"Enter size to close (max {selected_pos.size})", "float")
        if not size_input:
            return
        
        size_val = float(size_input)
        if size_val <= 0 or size_val > selected_pos.size:
            print(f"❌ Size must be between 0 and {selected_pos.size}")
            return
        
        slippage = get_user_input("Enter slippage % (e.g. 0.5 for 0.5%)", "float")
        if not slippage:
            return
        
        slippage_val = float(slippage) / 100
        
        print(f"\n📋 Close Order Summary:")
        print(f"   Symbol: {selected_pos.symbol}")
        print(f"   Position: {selected_pos.side.value.upper()}")
        print(f"   Size to close: {size_val}")
        print(f"   Slippage: {slippage_val*100:.1f}%")
        
        confirm = input("\n⚠️  Proceed with closing? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Close order cancelled")
            return
        
        print("\n🔄 Closing position...")
        
        # Double-check position still exists before attempting to close
        current_positions = await connector.get_open_positions()
        position_exists = any(
            pos.symbol == selected_pos.symbol and 
            pos.side == selected_pos.side and 
            pos.size >= size_val 
            for pos in current_positions
        )
        
        if not position_exists:
            print("❌ Position no longer exists or insufficient size available")
            return
        
        if selected_pos.side.value == "buy":
            order = await connector.close_buy_position(selected_pos.symbol, size_val, slippage_val)
        else:
            order = await connector.close_sell_position(selected_pos.symbol, size_val, slippage_val)
        
        print(f"✅ Position closed successfully!")
        print(f"   Order ID: {order.id}")
        print(f"   Size: {order.size}")
        print(f"   Price: ${order.price:.2f}")
        print(f"   Total: ${order.size * order.price:.2f}")
        
    except Exception as e:
        print(f"❌ Close failed: {e}")

async def setup_trading_command(connector: LighterConnector):
    """Setup trading (generate API keys)"""
    print("\n🔧 SETUP TRADING")
    print("=" * 40)
    print("This will setup trading using the environment variables")
    
    confirm = input("⚠️  Proceed with setup? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Setup cancelled")
        return False
    
    try:
        print("🔄 Setting up trading...")
        success = await connector.setup_trading()
        
        if success:
            print("✅ Trading setup completed successfully!")
            return True
        else:
            print("❌ Trading setup failed")
            return False
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

async def view_positions_command(connector: LighterConnector):
    """Display all current positions"""
    print("\n📊 POSITION OVERVIEW")
    print("=" * 40)
    
    try:
        positions = await connector.get_open_positions()
        
        if not positions:
            print("📭 No open positions")
            print("   Ready to trade! Use 'Market Open' to create a position.")
            return
        
        print(f"📈 {len(positions)} open position(s):")
        print()
        
        total_pnl = 0
        for i, pos in enumerate(positions):
            side_str = "🟢 LONG" if pos.side.value == "buy" else "🔴 SHORT"
            pnl_str = f"${pos.unrealized_pnl:+.2f}" if pos.unrealized_pnl != 0 else "$0.00"
            leverage_str = f"{pos.leverage:.1f}x" if hasattr(pos, 'leverage') else "1.0x"
            
            # Calculate position value
            position_value = pos.size * pos.current_price
            
            print(f"   {i+1}. {pos.symbol}")
            print(f"      Side: {side_str}")
            print(f"      Size: {pos.size}")
            print(f"      Entry Price: ${pos.entry_price:.2f}")
            print(f"      Current Price: ${pos.current_price:.2f}")
            print(f"      Position Value: ${position_value:.2f}")
            print(f"      Leverage: {leverage_str}")
            print(f"      Unrealized PnL: {pnl_str}")
            print()
            
            total_pnl += pos.unrealized_pnl
        
        # Show total PnL
        total_pnl_str = f"${total_pnl:+.2f}" if total_pnl != 0 else "$0.00"
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        print(f"{pnl_emoji} Total Unrealized PnL: {total_pnl_str}")
        
    except Exception as e:
        print(f"❌ Failed to fetch positions: {e}")

def show_menu(is_authenticated: bool = True):
    """Show main menu"""
    print("\n🚀 LIGHTER CLI")
    print("=" * 30)
    
    if not is_authenticated:
        print("⚠️  Authentication required")
        print("1. Setup/authenticate")
        print("2. Exit")
    else:
        print("1. Market Open (buy/sell)")
        print("2. Market Close")
        print("3. View Positions")
        print("4. Re-authenticate/setup")
        print("5. Exit")
    print()

async def main():
    """Main CLI loop"""
    # Load environment
    load_dotenv('.env.local')
    
    # Create connector
    connector = create_connector()
    if not connector:
        return
    
    print("✅ Lighter connector initialized")
    print(f"   Endpoint: {connector.base_endpoint}")
    print(f"   Address: {connector.l1_address}")
    
    # Track authentication state
    is_authenticated = False
    
    while True:
        try:
            show_menu(is_authenticated)
            
            if not is_authenticated:
                choice = input("Select option (1-2): ").strip()
                if choice == '1':
                    is_authenticated = await setup_trading_command(connector)
                elif choice == '2':
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid option. Please authenticate first (option 1) or exit (option 2).")
            else:
                choice = input("Select option (1-5): ").strip()
                if choice == '1':
                    await market_open_command(connector)
                elif choice == '2':
                    await market_close_command(connector)
                elif choice == '3':
                    await view_positions_command(connector)
                elif choice == '4':
                    is_authenticated = await setup_trading_command(connector)
                elif choice == '5':
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid option. Please select 1-5.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    # Clean up
    try:
        if hasattr(connector, 'signer_client') and connector.signer_client:
            await connector.signer_client.close()
    except:
        pass

if __name__ == '__main__':
    asyncio.run(main())
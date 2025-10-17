#!/usr/bin/env python3
"""
Test script to debug Lighter connector position fetching
"""

import asyncio
import os
import requests
from dotenv import load_dotenv
from utils.connectors.lighter.lighter_connector import LighterConnector

async def test_positions():
    """Test position fetching with detailed debugging"""
    
    # Load environment
    load_dotenv('.env.local')
    
    base_endpoint = os.getenv('LIGHTER_BASE_ENDPOINT')
    private_key = os.getenv('LIGHTER_PRIVATE_KEY')
    l1_address = os.getenv('LIGHTER_L1_ADDRESS')
    
    print("🔧 Testing Lighter Connector Position Fetching")
    print("=" * 50)
    print(f"Endpoint: {base_endpoint}")
    print(f"L1 Address: {l1_address}")
    print()
    
    # Create connector
    try:
        connector = LighterConnector(
            base_endpoint=base_endpoint,
            private_key=private_key,
            l1_address=l1_address
        )
        print("✅ Connector created successfully")
        print(f"Account Index: {connector.account_index}")
        print()
    except Exception as e:
        print(f"❌ Failed to create connector: {e}")
        return
    
    # Test 1: Direct API call to account endpoint
    print("🔍 Test 1: Direct account API call")
    try:
        if connector.account_index is not None:
            response = requests.get(f"{base_endpoint}/api/v1/account", 
                                  params={'account_index': connector.account_index})
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            print()
        else:
            print("❌ No account index available")
            print()
    except Exception as e:
        print(f"❌ Direct API call failed: {e}")
        print()
    
    # Test 2: Try different account endpoint format
    print("🔍 Test 2: Alternative account endpoint")
    try:
        # Try the same format used in _fetch_account_index
        response = requests.get(f"{base_endpoint}/api/v1/account", 
                              params={'by': 'l1_address', 'value': l1_address})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}...")
        print()
    except Exception as e:
        print(f"❌ Alternative API call failed: {e}")
        print()
    
    # Test 3: Try account endpoint without params
    print("🔍 Test 3: Account endpoint without params")
    try:
        response = requests.get(f"{base_endpoint}/api/v1/account")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        print()
    except Exception as e:
        print(f"❌ No params API call failed: {e}")
        print()
    
    # Test 4: List available endpoints
    print("🔍 Test 4: Test other endpoints")
    endpoints_to_test = [
        "/api/v1/accounts",
        "/api/v1/positions", 
        "/api/v1/orderBooks",
        "/api/v1/account-info"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{base_endpoint}{endpoint}")
            print(f"{endpoint}: {response.status_code}")
            if response.status_code == 200:
                print(f"  Response: {response.text[:200]}...")
        except Exception as e:
            print(f"{endpoint}: Error - {e}")
        print()
    
    # Test 5: Use connector's get_open_positions method
    print("🔍 Test 5: Connector get_open_positions method")
    try:
        positions = await connector.get_open_positions()
        print(f"✅ Positions fetched: {len(positions)}")
        for pos in positions:
            print(f"  {pos.symbol}: {pos.side.value} {pos.size} @ ${pos.entry_price}")
    except Exception as e:
        print(f"❌ get_open_positions failed: {e}")
    
    print("\n🏁 Test completed")

if __name__ == '__main__':
    asyncio.run(test_positions())
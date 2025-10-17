#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from utils.connectors.lighter.lighter_connector import LighterConnector
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv('.env.local')

async def test_lighter_funding_rate():
    """Test Lighter funding rate API and show raw response"""
    
    # Initialize connector (without trading setup for API-only testing)
    connector = LighterConnector(
        base_endpoint=os.getenv('LIGHTER_BASE_ENDPOINT'),
        private_key=os.getenv('LIGHTER_PRIVATE_KEY'),
        l1_address=os.getenv('LIGHTER_L1_ADDRESS')
    )
    
    symbol = "ETH"
    
    print(f"Testing Lighter funding rate API for {symbol}")
    print("=" * 60)
    
    try:
        # Test raw funding rates endpoint first
        base_url = connector.base_endpoint.rstrip('/')
        print(f"Base URL: {base_url}")
        print(f"Testing endpoint: {base_url}/api/v1/funding-rates")
        print()
        
        # Get raw API response - try with exchange parameter
        response = requests.get(f"{base_url}/api/v1/funding-rates", params={'exchange': 'lighter'})
        response.raise_for_status()
        raw_data = response.json()
        
        print("Raw API Response:")
        print(f"Response type: {type(raw_data)}")
        if isinstance(raw_data, dict):
            print(f"Response keys: {list(raw_data.keys())}")
            funding_rates = raw_data.get('funding_rates', [])
            print(f"Number of funding rates: {len(funding_rates)}")
            print()
            
            # Show first few funding rates for analysis
            print("First 3 funding rate entries:")
            for i, funding_rate in enumerate(funding_rates[:3]):
                print(f"  Entry {i+1}: {funding_rate}")
            print()
            
            # Look for both Binance and Lighter rates for the symbol
            if symbol in connector._symbol_to_market_id_cache:
                market_id = connector._symbol_to_market_id_cache[symbol]
                print(f"Looking for {symbol} with market_id: {market_id}")
                
                binance_rate = None
                lighter_rate = None
                
                for funding_rate in funding_rates:
                    if funding_rate.get('market_id') == market_id:
                        if funding_rate.get('exchange') == 'binance':
                            binance_rate = funding_rate
                        elif funding_rate.get('exchange') == 'lighter':
                            lighter_rate = funding_rate
                
                # Show both if available
                if binance_rate:
                    rate_float = float(binance_rate['rate'])
                    print(f"\n{symbol} BINANCE Funding Rate:")
                    print(f"  Market ID: {binance_rate.get('market_id')}")
                    print(f"  Exchange: {binance_rate.get('exchange')}")
                    print(f"  Raw rate: {binance_rate['rate']}")
                    print(f"  As percentage: {rate_float * 100:.6f}%")
                    print(f"  Full entry: {binance_rate}")
                
                if lighter_rate:
                    rate_float = float(lighter_rate['rate'])
                    print(f"\n{symbol} LIGHTER Funding Rate:")
                    print(f"  Market ID: {lighter_rate.get('market_id')}")
                    print(f"  Exchange: {lighter_rate.get('exchange')}")
                    print(f"  Raw rate: {lighter_rate['rate']}")
                    print(f"  As percentage: {rate_float * 100:.6f}%")
                    print(f"  Full entry: {lighter_rate}")
                
                if not binance_rate and not lighter_rate:
                    print(f"No funding rate found for {symbol} (market_id: {market_id})")
                elif not lighter_rate:
                    print(f"No Lighter-specific funding rate found for {symbol}")
                    
                # Check all exchanges available for this market_id
                exchanges_for_market = [fr['exchange'] for fr in funding_rates if fr.get('market_id') == market_id]
                print(f"Available exchanges for market_id {market_id}: {set(exchanges_for_market)}")
            else:
                print(f"Symbol {symbol} not found in market cache")
                print(f"Available symbols: {list(connector._symbol_to_market_id_cache.keys())}")
        
        # Test using connector method
        print(f"\n{'='*40}")
        print("Testing connector method:")
        try:
            funding_rate = await connector.get_current_funding_rate(symbol)
            
            print(f"Symbol: {funding_rate.symbol}")
            print(f"Rate: {funding_rate.rate}")
            print(f"Rate (scientific): {funding_rate.rate:.10e}")
            print(f"Rate (decimal): {funding_rate.rate:.10f}")
            print(f"Timestamp: {funding_rate.timestamp}")
            print(f"Next funding time: {funding_rate.next_funding_time}")
        except Exception as connector_error:
            print(f"Connector method failed: {connector_error}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_lighter_funding_rate())
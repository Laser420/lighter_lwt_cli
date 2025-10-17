#!/usr/bin/env python3

import asyncio
import os
import sys
sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
from utils.connectors.lighter.lighter_connector import LighterConnector

async def debug_trading_setup():
    """Debug the trading setup process to see specific errors"""
    
    load_dotenv('.env.local')
    
    base_endpoint = os.getenv('LIGHTER_BASE_ENDPOINT')
    private_key = os.getenv('LIGHTER_PRIVATE_KEY')
    l1_address = os.getenv('LIGHTER_L1_ADDRESS')
    
    print("🔍 DEBUG: Trading Setup Process")
    print("=" * 50)
    
    print(f"Base endpoint: {base_endpoint}")
    print(f"L1 address: {l1_address}")
    print(f"Private key available: {'Yes' if private_key else 'No'}")
    print()
    
    try:
        # Initialize connector
        connector = LighterConnector(
            base_endpoint=base_endpoint,
            l1_address=l1_address,
            private_key=private_key
        )
        print(f"✅ Connector initialized")
        print(f"   Account index: {connector.account_index}")
        print()
        
        # Check required parameters for setup_trading
        print("🔍 Checking setup_trading requirements:")
        print(f"   base_endpoint: {'✅' if connector.base_endpoint else '❌'} {connector.base_endpoint}")
        print(f"   eth_private_key: {'✅' if connector.eth_private_key else '❌'}")
        print(f"   account_index: {'✅' if connector.account_index is not None else '❌'} {connector.account_index}")
        print(f"   api_key_index: {'✅' if connector.api_key_index is not None else '❌'} {connector.api_key_index}")
        print()
        
        # Try setup_trading with detailed error handling
        print("🔧 Attempting setup_trading...")
        try:
            # Manual setup_trading with detailed error reporting
            if not all([connector.base_endpoint, connector.eth_private_key, connector.account_index is not None, connector.api_key_index is not None]):
                print("❌ Missing required parameters:")
                if not connector.base_endpoint:
                    print("   - base_endpoint missing")
                if not connector.eth_private_key:
                    print("   - eth_private_key missing") 
                if connector.account_index is None:
                    print("   - account_index missing")
                if connector.api_key_index is None:
                    print("   - api_key_index missing")
                return
            
            print("✅ All required parameters present")
            
            # Try to import lighter SDK components
            print("🔍 Testing lighter SDK imports...")
            try:
                import lighter
                print("✅ lighter module imported")
                
                # Test API key generation
                api_private_key, api_public_key, err = lighter.create_api_key()
                if err:
                    print(f"❌ API key generation failed: {err}")
                    return
                print("✅ API key generation successful")
                print(f"   API private key length: {len(api_private_key) if api_private_key else 0}")
                print(f"   API public key length: {len(api_public_key) if api_public_key else 0}")
                
                # Test SignerClient creation
                print("🔍 Testing SignerClient creation...")
                temp_client = lighter.SignerClient(
                    url=connector.base_endpoint,
                    private_key=api_private_key,
                    account_index=connector.account_index,
                    api_key_index=connector.api_key_index,
                    nonce_management_type=lighter.nonce_manager.NonceManagerType.API
                )
                print("✅ SignerClient created successfully")
                
                # Test API key registration
                print("🔍 Testing API key registration...")
                response, err = await temp_client.change_api_key(
                    eth_private_key=connector.eth_private_key,
                    new_pubkey=api_public_key
                )
                
                if err:
                    print(f"❌ API key registration failed: {err}")
                    await temp_client.close()
                    return
                
                print("✅ API key registration successful")
                print(f"   Response: {response}")
                
                # Clean up
                await temp_client.close()
                print("✅ Trading setup would succeed")
                
            except ImportError as e:
                print(f"❌ lighter SDK import failed: {e}")
                return
            except Exception as e:
                print(f"❌ SDK operation failed: {e}")
                import traceback
                traceback.print_exc()
                return
                
        except Exception as e:
            print(f"❌ Setup trading failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        print(f"❌ Connector initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_trading_setup())
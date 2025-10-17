# Lighter CLI - LLM Context

## Project Overview

This is a command-line interface (CLI) application for trading on the Lighter DEX (Decentralized Exchange) on Arbitrum. It provides a simple, interactive way to manage cryptocurrency positions without needing a web interface.

## What is Lighter DEX?

Lighter DEX is a decentralized derivatives exchange built on Arbitrum that allows users to trade perpetual futures with leverage. It uses an API-based trading system with authentication via Ethereum private keys.

## Project Architecture

### Core Components

1. **Main CLI (`lighter_cli.py`)** - Interactive command-line interface with menu system
2. **Lighter Connector (`utils/connectors/lighter/lighter_connector.py`)** - Handles all API interactions with Lighter DEX
3. **Base Connector (`utils/connectors/base_connector.py`)** - Abstract base class defining trading interface
4. **Environment Configuration (`.env.local`)** - Stores API endpoints and credentials

### Key Features

- **Authentication Flow**: Requires setup/authentication before trading
- **Market Orders**: Buy/sell with configurable leverage and slippage
- **Position Management**: View, close, and monitor open positions
- **Real-time Data**: Current prices, PnL calculations, position details
- **Safety Features**: Input validation, confirmation prompts, error handling

## CLI Menu Structure

### Unauthenticated State
```
1. Setup/authenticate
2. Exit
```

### Authenticated State
```
1. Market Open (buy/sell)
2. Market Close
3. View Positions
4. Re-authenticate/setup
5. Exit
```

## Trading Workflow

### Opening a Position
1. Select "Market Open" from menu
2. Enter symbol (e.g., ETH, BTC)
3. Choose side (buy/sell)
4. Specify size in base asset
5. Set slippage percentage
6. Set leverage (default: 1x)
7. Confirm order details
8. Execute trade

### Viewing Positions
- Displays all open positions with:
  - Symbol and side (LONG/SHORT)
  - Position size and entry price
  - Current market price and position value
  - Leverage multiplier
  - Unrealized PnL
  - Total portfolio PnL

### Closing Positions
1. Select "Market Close" from menu
2. Choose position from list
3. Specify size to close (partial or full)
4. Set slippage percentage
5. Confirm close order
6. Execute close trade

## Technical Implementation

### API Integration
- Uses Lighter Python SDK for order execution
- Direct REST API calls for market data and positions
- Handles API key generation and registration
- Manages nonce and transaction tracking

### Data Models
- **Position**: Symbol, side, size, prices, leverage, PnL, timestamp
- **Order**: ID, symbol, side, type, size, price, status, timestamp
- **Price**: Symbol, current price, timestamp

### Error Handling
- Network connectivity issues
- Invalid user inputs
- API errors and rate limits
- Authentication failures
- Position validation (e.g., insufficient size)

### Security Features
- Private keys stored in environment variables
- API key rotation capability
- Transaction confirmation before execution
- Input validation and sanitization

## Environment Variables

Required in `.env.local`:
```bash
LIGHTER_BASE_ENDPOINT=https://mainnet.zklighter.elliot.ai/
LIGHTER_PRIVATE_KEY=0x... # Ethereum private key
LIGHTER_L1_ADDRESS=0x... # Ethereum wallet address
LIGHTER_API_KEY_INDEX=0
LIGHTER_POLL_INTERVAL=0.05
LIGHTER_FILL_TIMEOUT=3
```

## Dependencies

### Core Dependencies
- **lighter**: Official Lighter DEX Python SDK
- **python-dotenv**: Environment variable management
- **requests**: HTTP client for API calls
- **asyncio**: Asynchronous programming support

### Development Dependencies
- Standard Python libraries (os, sys, json, time, datetime)
- Type hints (typing module)
- Data classes and enums

## Common Issues and Solutions

### Position Fetching
- **Issue**: API endpoint format mismatch
- **Solution**: Use `by=l1_address&value=<address>` format instead of direct account_index

### Debug Logging
- **Issue**: Verbose debug output from external libraries
- **Solution**: Comprehensive logging suppression configured in main CLI

### Asyncio Import
- **Issue**: Missing asyncio import causing transaction confirmation failures
- **Solution**: Added asyncio import to lighter connector

### Input Validation
- **Issue**: Non-numeric input causing position selection errors
- **Solution**: Added `.isdigit()` validation for position selection

## File Structure
```
├── lighter_cli.py              # Main CLI application
├── utils/
│   └── connectors/
│       ├── base_connector.py   # Abstract trading interface
│       └── lighter/
│           └── lighter_connector.py  # Lighter DEX implementation
├── requirements.txt            # Python dependencies
├── .env.local                 # Environment configuration
├── README.md                  # User documentation
└── llm_context.md            # This file
```

## Development Notes

### For LLM Assistants
- Always check position data structure when modifying position-related features
- Leverage is calculated from `initial_margin_fraction` (100/margin_fraction)
- The CLI uses async/await pattern for all trading operations
- Error handling should be comprehensive but user-friendly
- Input validation is critical for financial operations

### Recent Improvements
- Added leverage support for position opening
- Implemented position overview functionality
- Fixed API endpoint issues for position fetching
- Enhanced input validation and error handling
- Cleaned up debug logging for professional UX
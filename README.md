# Lighter CLI

A command-line interface for trading on Lighter DEX (Arbitrum). Simple, interactive, and powerful.

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd lighter_lwt_cli

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install git+https://github.com/elliottech/lighter-python.git
```

### 2. Configuration

Create `.env.local` file:
```bash
LIGHTER_BASE_ENDPOINT=https://mainnet.zklighter.elliot.ai/
LIGHTER_PRIVATE_KEY=0x...  # Your Ethereum private key
LIGHTER_L1_ADDRESS=0x...   # Your Ethereum address
LIGHTER_API_KEY_INDEX=0
LIGHTER_POLL_INTERVAL=0.05
LIGHTER_FILL_TIMEOUT=3
```

### 3. Run the CLI

```bash
python lighter_cli.py
```

## Features

- 🔐 **Secure Authentication** - Setup required before trading
- 📈 **Market Orders** - Buy/sell with custom leverage and slippage
- 👁️ **Position Overview** - View all positions with real-time PnL
- ⚡ **Quick Close** - Partial or full position closing
- 🛡️ **Input Validation** - Prevents accidental trades
- 🧹 **Clean Interface** - No debug noise, just essential info

## Menu Options

**After Authentication:**
1. **Market Open** - Create new positions
2. **Market Close** - Close existing positions  
3. **View Positions** - Overview of all positions
4. **Re-authenticate** - Setup new API keys
5. **Exit** - Close application

## Safety Features

- Confirmation prompts before every trade
- Input validation for all parameters
- Real-time price display before execution
- Position verification before closing
- Comprehensive error handling

## Support

For issues or questions, please check the `llm_context.md` file for detailed technical information.


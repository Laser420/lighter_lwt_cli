# Lighter CLI

A command-line interface for trading on Lighter DEX. Vibe-coded using components from a more sophisticated bot I've made. Does what it offers.

Please note that the one time this has failed is when both this CLI and the Lighter UI are authenticated at the same time with the same IP address. It gets confused. I think it's because the Lighter backend needs to predict nonces and it can't do that if two things may generate the same nonce.

### No warranties are made. Use both this tool and Lighter at your own risk, with non-essential funds

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

## Menu Options

**After Authentication:**
1. **Market Open** - Create new positions - also used for increasing existing position size
2. **Market Close** - Close existing positions - also used for decreasing existing position size
3. **View Positions** - Overview of all positions including size, leverage, direction and PnL
4. **Re-authenticate** - Redo the authentication process
5. **Exit** - Close application

## Safety Features

- Confirmation prompts before every trade
- Input validation for all parameters
- Real-time price display before execution
- Position verification before closing

## Support

For issues or questions, please check the `llm_context.md` file for detailed technical information. Or have your AI assistant check that file, but make sure it doesn't hallucinate.



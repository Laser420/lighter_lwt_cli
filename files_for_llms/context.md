# Lightweight Lighter CLI

A simple command-line interface for interacting with the Lighter DEX on Arbitrum.

## Quick Setup

### 1. Install Requirements

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Lighter SDK from GitHub (required)
pip install git+https://github.com/elliottech/lighter-python.git
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install requirements in venv
pip install -r requirements.txt
pip install git+https://github.com/elliottech/lighter-python.git
```

### 3. Environment Configuration

Create a `.env.local` file in the project root:

```bash
# Lighter DEX configuration
LIGHTER_BASE_ENDPOINT=https://api.lighter.xyz  # or your preferred endpoint
LIGHTER_PRIVATE_KEY=your_ethereum_private_key
LIGHTER_L1_ADDRESS=your_ethereum_address
LIGHTER_API_KEY_INDEX=0

# Optional: Performance tuning
LIGHTER_POLL_INTERVAL=0.05
LIGHTER_FILL_TIMEOUT=3
```

## Usage

### Basic Commands

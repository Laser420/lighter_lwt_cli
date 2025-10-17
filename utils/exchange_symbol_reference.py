#!/usr/bin/env python3
"""
Exchange Symbol Denomination Reference

This file documents how each exchange formats symbols for trading pairs.
Use this reference when configuring strategies to ensure correct symbol formats.

Updated: 2025-10-15
Based on: Live testing and connector validation
"""

EXCHANGE_SYMBOL_FORMATS = {
    "hyperliquid": {
        "description": "Uses simple coin symbols",
        "format": "{COIN}",
        "examples": {
            "ETH": "ETH",
            "BTC": "BTC", 
            "SOL": "SOL",
            "AVAX": "AVAX"
        },
        "notes": [
            "Always uppercase",
            "No quote currency in symbol",
            "Perpetual contracts implied"
        ]
    },
    
    "aster": {
        "description": "Uses coin + quote currency format",
        "format": "{COIN}{QUOTE}",
        "examples": {
            "ETH": "ETHUSDT",
            "BTC": "BTCUSDT",
            "BNB": "BNBUSDT",
            "SOL": "SOLUSDT"
        },
        "notes": [
            "Always uppercase", 
            "Quote currency typically USDT",
            "No separators between coin and quote"
        ]
    },
    
    "lighter": {
        "description": "Uses simple coin symbols",
        "format": "{COIN}",
        "examples": {
            "ETH": "ETH",
            "BTC": "BTC",
            "USDC": "USDC",
            "USDT": "USDT",
            "SOL": "SOL"
        },
        "notes": [
            "Always uppercase",
            "Similar to Hyperliquid format",
            "Market ID mapping handled internally"
        ]
    },
    
    "paradex": {
        "description": "Uses coin-quote-PERP format",
        "format": "{COIN}-{QUOTE}-PERP",
        "examples": {
            "ETH": "ETH-USD-PERP",
            "BTC": "BTC-USD-PERP", 
            "SOL": "SOL-USD-PERP",
            "ADA": "ADA-USD-PERP"
        },
        "notes": [
            "Always uppercase",
            "Uses hyphens as separators",
            "Explicit PERP suffix for perpetuals",
            "Quote currency typically USD"
        ]
    },
    
    "variational": {
        "description": "Format not yet validated",
        "format": "TBD",
        "examples": {},
        "notes": [
            "Connector implemented but not validated",
            "Need live testing to determine format"
        ]
    },
    
    "woofi": {
        "description": "Not yet implemented",
        "format": "TBD", 
        "examples": {},
        "notes": [
            "Placeholder connector only",
            "Multi-chain support planned"
        ]
    }
}
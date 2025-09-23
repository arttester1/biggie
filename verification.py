#!/usr/bin/env python3
"""
Verification Module - Extracted functions for both main bot and cron job
This module contains only the verification logic without bot initialization
"""

import logging
import json
import os
import asyncio
import re
import time
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Support Railway persistent volume via DATA_DIR
DATA_DIR = os.getenv("DATA_DIR", "/app/data" if os.path.exists("/app/data") else ".")

# Get admin user ID
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "1825755152")

# File paths
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
USER_DATA_PATH = os.path.join(DATA_DIR, "user_data.json")
WHITELIST_PATH = os.path.join(DATA_DIR, "whitelist.json")
PENDING_WHITELIST_PATH = os.path.join(DATA_DIR, "pending_whitelist.json")
REJECTED_GROUPS_PATH = os.path.join(DATA_DIR, "rejected_groups.json")

# Chain mapping for Moralis compatibility
CHAIN_MAP = {
    "eth": "eth",
    "mainnet": "eth",
    "0x1": "eth",
    "bsc": "bsc",
    "binance": "bsc",
    "0x38": "bsc",
    "polygon": "polygon",
    "matic": "polygon",
    "0x89": "polygon",
}

# ---------------------------------------------
# Token and Environment Setup
# ---------------------------------------------
def get_token_from_env():
    """Fetch secrets from environment variables or fallback .env file."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    moralis_key = os.getenv("MORALIS_API_KEY")
    etherscan_key = os.getenv("ETHERSCAN_API_KEY")

    # Fallback to .env file if not set
    if not (telegram_token and moralis_key and etherscan_key):
        try:
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TELEGRAM_BOT_TOKEN=") and not telegram_token:
                        telegram_token = line.split("=", 1)[1].strip()
                    elif line.startswith("MORALIS_API_KEY=") and not moralis_key:
                        moralis_key = line.split("=", 1)[1].strip()
                    elif line.startswith("ETHERSCAN_API_KEY=") and not etherscan_key:
                        etherscan_key = line.split("=", 1)[1].strip()
        except FileNotFoundError:
            pass

    return telegram_token, moralis_key, etherscan_key

# Get tokens
TOKEN, MORALIS_API_KEY, ETHERSCAN_API_KEY = get_token_from_env()

# ---------------------------------------------
# File Utilities
# ---------------------------------------------
def load_json_file(file_path):
    """Load JSON data from database or file (Railway-optimized)"""
    # Check if we have database connection (Railway PostgreSQL)
    if os.getenv("DATABASE_URL"):
        from database_simple import load_json_file as db_load
        return db_load(file_path)

    # Fallback to file system
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return {}
    return {}

def save_json_file(file_path, data):
    """Save JSON data to database or file (Railway-optimized)"""
    # Check if we have database connection (Railway PostgreSQL)
    if os.getenv("DATABASE_URL"):
        from database_simple import save_json_file as db_save
        return db_save(file_path, data)

    # Fallback to file system
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")
        return False

def is_owner(user_id):
    """Check if user is the bot owner."""
    return str(user_id) == ADMIN_USER_ID

# ---------------------------------------------
# Web3 and Balance Verification Functions
# ---------------------------------------------
async def get_token_decimals(token_address: str, chain_id: str = "eth") -> int:
    """Try to fetch decimals via Moralis, fallback to 18 if not available."""
    try:
        from moralis import evm_api
        moralis_chain = CHAIN_MAP.get(chain_id, chain_id)
        params = {
            "chain": moralis_chain,
            "addresses": [token_address]
        }
        token_metadata = await asyncio.to_thread(
            evm_api.token.get_token_metadata,
            api_key=MORALIS_API_KEY,
            params=params
        )
        decimals = int(token_metadata[0].get("decimals", 18))
        return decimals
    except Exception as e:
        logger.error(f"Error fetching token decimals: {e}")
        return 18

async def get_token_balance_moralis(wallet: str, token: str, chain: str = "eth") -> float:
    """Get token balance using Moralis SDK"""
    try:
        from moralis import evm_api
        params = {
            "address": wallet,
            "chain": chain,
            "token_addresses": [token]
        }

        result = await asyncio.to_thread(
            evm_api.token.get_wallet_token_balances,
            api_key=MORALIS_API_KEY,
            params=params
        )

        if result and isinstance(result, list):
            for token_data in result:
                if token_data.get('token_address', '').lower() == token.lower():
                    raw_balance = int(token_data.get('balance', 0))
                    decimals = int(token_data.get('decimals', 18))
                    return raw_balance / (10 ** decimals)

        return 0.0

    except Exception as e:
        logger.error(f"Moralis SDK error: {e}")
        return 0.0

async def get_token_balance_etherscan(wallet: str, token: str) -> float:
    """Get token balance using Etherscan V2 REST API (with chainid=1)."""
    if not ETHERSCAN_API_KEY:
        logger.warning("No ETHERSCAN_API_KEY found, skipping fallback API.")
        return 0.0

    import aiohttp
    url = (
        f"https://api.etherscan.io/v2/api"
        f"?chainid=1"
        f"&module=account"
        f"&action=tokenbalance"
        f"&contractaddress={token}"
        f"&address={wallet}"
        f"&tag=latest"
        f"&apikey={ETHERSCAN_API_KEY}"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                result = await resp.json()
                raw_balance = int(result.get("result", "0"))
                return raw_balance  # Divide by decimals elsewhere!
    except Exception as e:
        logger.error(f"Etherscan V2 REST error: {e}")
    return 0.0

async def verify_user_balance(group_config, user_address):
    """Verify if user meets token balance requirements with proper fallback"""
    try:
        token_address = group_config["token"]
        min_balance = group_config["min_balance"]
        chain_id = group_config.get("chain_id", "eth")

        logger.info(f"🔍 Checking balance for {user_address} on {chain_id}")
        logger.info(f"Token: {token_address}, Min required: {min_balance}")

        balance = 0.0

        # Only try Moralis if we have a valid-looking API key
        if MORALIS_API_KEY and len(MORALIS_API_KEY) > 50:  # Basic validation
            try:
                moralis_chain = CHAIN_MAP.get(chain_id, chain_id)
                logger.info(f"Using Moralis API for balance check on {moralis_chain}")
                balance = await get_token_balance_moralis(user_address, token_address, moralis_chain)
                logger.info(f"Moralis balance result: {balance}")
                if balance > 0:
                    logger.info("✅ Moralis balance check successful")
            except Exception as e:
                logger.warning(f"⚠️ Moralis failed, falling back to RPC: {e}")

        # If Moralis failed or returned 0, try Etherscan fallback
        if balance <= 0:
            logger.info("🔄 Using Etherscan fallback verification")
            etherscan_balance_raw = await get_token_balance_etherscan(user_address, token_address)
            # Get correct decimals
            decimals = await get_token_decimals(token_address, chain_id)
            balance = etherscan_balance_raw / (10 ** decimals)
            logger.info(f"Etherscan balance result: {balance}")

        logger.info(f"📊 Final balance: {balance}, Required: {min_balance}, Sufficient: {balance >= min_balance}")

        return balance >= min_balance
    except Exception as e:
        logger.error(f"❌ Error in verify_user_balance: {e}")
        return False

# ---------------------------------------------
# 3-Strike Rejection Tracking System
# ---------------------------------------------
def track_rejection(group_id, group_name=None, admin_id=None, admin_name=None):
    """Track a rejection for a group. Returns True if group should be blocked (3+ strikes)."""
    rejected_groups = load_json_file(REJECTED_GROUPS_PATH)
    current_time = int(time.time())

    if group_id not in rejected_groups:
        rejected_groups[group_id] = {
            "rejection_count": 0,
            "group_name": group_name or f"Group {group_id}",
            "last_admin_id": admin_id,
            "last_admin_name": admin_name or "Unknown",
            "first_rejection": current_time,
            "last_rejection": current_time,
            "blocked": False
        }

    # Increment rejection count
    rejected_groups[group_id]["rejection_count"] += 1
    rejected_groups[group_id]["last_rejection"] = current_time

    # Update admin info if provided
    if admin_id:
        rejected_groups[group_id]["last_admin_id"] = admin_id
    if admin_name:
        rejected_groups[group_id]["last_admin_name"] = admin_name
    if group_name:
        rejected_groups[group_id]["group_name"] = group_name

    # Check if should be blocked (3+ rejections)
    if rejected_groups[group_id]["rejection_count"] >= 3:
        rejected_groups[group_id]["blocked"] = True

    save_json_file(REJECTED_GROUPS_PATH, rejected_groups)
    return rejected_groups[group_id]["blocked"]

def is_group_blocked(group_id):
    """Check if a group is blocked due to 3+ rejections."""
    rejected_groups = load_json_file(REJECTED_GROUPS_PATH)
    group_data = rejected_groups.get(group_id, {})
    return group_data.get("blocked", False)

def get_rejection_count(group_id):
    """Get the current rejection count for a group."""
    rejected_groups = load_json_file(REJECTED_GROUPS_PATH)
    group_data = rejected_groups.get(group_id, {})
    return group_data.get("rejection_count", 0)

def reset_rejection_count(group_id):
    """Reset rejection count for a group (admin function)."""
    rejected_groups = load_json_file(REJECTED_GROUPS_PATH)
    if group_id in rejected_groups:
        rejected_groups[group_id]["rejection_count"] = 0
        rejected_groups[group_id]["blocked"] = False
        return save_json_file(REJECTED_GROUPS_PATH, rejected_groups)
    return True

def get_blocked_groups():
    """Get all blocked groups for admin commands."""
    rejected_groups = load_json_file(REJECTED_GROUPS_PATH)
    blocked = {}
    for group_id, data in rejected_groups.items():
        if data.get("blocked", False):
            blocked[group_id] = data
    return blocked

def get_all_rejections():
    """Get all groups with rejections (for admin viewing)."""
    return load_json_file(REJECTED_GROUPS_PATH)

# ---------------------------------------------
# Whitelist Management Functions
# ---------------------------------------------
def is_group_whitelisted(group_id):
    """Check if group is whitelisted."""
    whitelist = load_json_file(WHITELIST_PATH)
    return group_id in whitelist

def whitelist_group(group_id):
    """Add group to whitelist."""
    whitelist = load_json_file(WHITELIST_PATH)
    whitelist[group_id] = True
    return save_json_file(WHITELIST_PATH, whitelist)

def add_pending_whitelist(group_id, group_name, admin_id, admin_name):
    """Add group to pending whitelist."""
    pending = load_json_file(PENDING_WHITELIST_PATH)
    pending[group_id] = {
        "group_name": group_name,
        "admin_id": admin_id,
        "admin_name": admin_name,
        "timestamp": int(time.time())
    }
    return save_json_file(PENDING_WHITELIST_PATH, pending)

def remove_pending_whitelist(group_id):
    """Remove group from pending whitelist."""
    pending = load_json_file(PENDING_WHITELIST_PATH)
    if group_id in pending:
        del pending[group_id]
        return save_json_file(PENDING_WHITELIST_PATH, pending)
    return True
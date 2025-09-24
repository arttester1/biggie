#!/usr/bin/env python3
"""
Railway Cron Job for Periodic User Verification
This script runs as a separate Railway service with cron schedule: "0 */6 * * *"
"""

import logging
import sys
import asyncio
from typing import Dict, Any
from telegram import Bot

# Import verification functions from verification module (no bot initialization)
from verification import (
    load_json_file, save_json_file, verify_user_balance, is_owner,
    CONFIG_PATH, USER_DATA_PATH, get_token_from_env
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get bot token
TOKEN, _, _ = get_token_from_env()
if not TOKEN:
    logger.error("ERROR: Could not find TELEGRAM_BOT_TOKEN")
    sys.exit(1)

async def verify_all_members(bot: Bot, group_id: str, group_config: Dict[str, Any]):
    """Verify all existing group members against token requirements."""
    try:
        logger.info(f"🔄 Starting periodic verification for group {group_id}")
        logger.info(f"📊 Using config: min_balance={group_config.get('min_balance')}, token={group_config.get('token')}")

        user_data = load_json_file(USER_DATA_PATH)
        group_users = user_data.get(group_id, {})

        logger.info(f"Found {len(group_users)} users to verify in group {group_id}")

        verified_count = 0
        removed_count = 0
        error_count = 0

        for user_id, user_info in group_users.items():
            # Skip owner - permanent access
            if is_owner(int(user_id)):
                logger.info(f"Skipping owner {user_id}")
                continue

            if user_info.get("verified"):
                user_address = user_info["address"]
                logger.info(f"Verifying user {user_id} with address {user_address}")

                has_balance = await verify_user_balance(group_config, user_address)

                if not has_balance:
                    logger.info(f"❌ User {user_id} has insufficient balance, removing...")
                    try:
                        # User no longer meets requirements, remove them
                        await bot.ban_chat_member(chat_id=group_id, user_id=int(user_id))
                        await bot.unban_chat_member(chat_id=group_id, user_id=int(user_id))

                        # Update user data
                        user_data[group_id][user_id]["verified"] = False
                        save_json_file(USER_DATA_PATH, user_data)

                        removed_count += 1
                        logger.info(f"✅ Successfully removed user {user_id}")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"❌ Error removing user {user_id}: {e}")
                else:
                    verified_count += 1
                    logger.info(f"✅ User {user_id} still has sufficient balance")

        logger.info(f"📊 Verification completed: {verified_count} verified, {removed_count} removed, {error_count} errors")

    except Exception as e:
        logger.error(f"❌ Error in periodic verification for group {group_id}: {e}")

async def periodic_verification():
    """Periodically verify all members in configured groups."""
    # ALWAYS reload fresh config from database/file
    config = load_json_file(CONFIG_PATH)

    if not config:
        logger.info("No groups configured for verification")
        return

    logger.info(f"🔄 Starting periodic verification cycle for {len(config)} groups")

    # Log the actual config values being used
    for gid, gconf in config.items():
        logger.info(f"📋 Group {gid} config: token={gconf.get('token')}, min_balance={gconf.get('min_balance')}")

    # Create bot instance
    bot = Bot(token=TOKEN)

    for group_id, group_config in config.items():
        logger.info(f"Verifying members in group {group_id}")
        # Reload config for each group to ensure fresh data
        fresh_config = load_json_file(CONFIG_PATH)
        fresh_group_config = fresh_config.get(group_id, group_config)
        await verify_all_members(bot, group_id, fresh_group_config)

    logger.info("✅ Periodic verification cycle completed")

async def main():
    """Main function for cron job."""
    logger.info("🚀 Starting Railway cron verification job")

    try:
        await periodic_verification()
        logger.info("✅ Cron verification job completed successfully")
    except Exception as e:
        logger.error(f"❌ Cron verification job failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Telegram Bot Test - Step by Step Diagnostics
"""

print("🔴 TELEGRAM TEST START")

# Step 1: Basic Python
print("✅ Step 1: Python execution works")

# Step 2: Environment variables
import os
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
print(f"✅ Step 2: Environment - TOKEN exists: {bool(telegram_token)}")

if not telegram_token:
    print("❌ TELEGRAM_BOT_TOKEN missing - this would cause main.py to crash")
    exit(1)

# Step 3: Import telegram
try:
    from telegram import Bot
    print("✅ Step 3: Telegram import successful")
except Exception as e:
    print(f"❌ Step 3: Telegram import failed: {e}")
    exit(1)

# Step 4: Create bot instance
try:
    bot = Bot(token=telegram_token)
    print("✅ Step 4: Bot instance created")
except Exception as e:
    print(f"❌ Step 4: Bot creation failed: {e}")
    print("This could be token issue or network issue")
    exit(1)

# Step 5: Test async functionality
import asyncio

async def test_bot():
    try:
        me = await bot.get_me()
        print(f"✅ Step 5: Bot API test successful - Bot name: {me.first_name}")
        return True
    except Exception as e:
        print(f"❌ Step 5: Bot API test failed: {e}")
        return False

# Run async test
try:
    result = asyncio.run(test_bot())
    if result:
        print("🟢 ALL TESTS PASSED - Your bot should work!")
    else:
        print("🔴 BOT API FAILED - Check token or network")
except Exception as e:
    print(f"❌ Async test failed: {e}")

print("🔴 TELEGRAM TEST END")
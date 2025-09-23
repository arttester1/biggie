#!/usr/bin/env python3
"""
Minimal Railway Test Script - Isolate the Issue
"""

print("🔴 MINIMAL TEST START")
print("Python is working!")
print("Environment test:")

import os
import sys

print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir('.')}")

# Test environment variables
print(f"TELEGRAM_BOT_TOKEN exists: {'TELEGRAM_BOT_TOKEN' in os.environ}")
print(f"DATA_DIR: {os.getenv('DATA_DIR', 'NOT_SET')}")

print("🟢 MINIMAL TEST SUCCESS - If you see this, Python works")

# Test if we can import telegram
try:
    import telegram
    print("✅ Telegram import works")
except ImportError as e:
    print(f"❌ Telegram import failed: {e}")
except Exception as e:
    print(f"❌ Unexpected telegram import error: {e}")

print("🔴 MINIMAL TEST END")
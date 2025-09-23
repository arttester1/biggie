#!/usr/bin/env python3
"""
Test verification.py integration with database_simple.py
"""

import os
import sys
import tempfile
import shutil

def test_verification_integration():
    """Test verification.py with database integration"""
    print("🧪 Testing Verification.py Integration...")

    test_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()

    try:
        os.chdir(test_dir)
        sys.path.insert(0, original_dir)

        # Test 1: Import verification module
        print("\n1️⃣ Testing verification.py import...")
        from verification import (
            load_json_file, save_json_file,
            is_group_blocked, track_rejection,
            get_rejection_count, reset_rejection_count,
            CONFIG_PATH, USER_DATA_PATH, REJECTED_GROUPS_PATH
        )
        print("✅ Verification module imported successfully")

        # Test 2: Test WITHOUT DATABASE_URL (file mode)
        print("\n2️⃣ Testing file mode (no DATABASE_URL)...")
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        # Create a config
        test_config = {
            "group1": {
                "chain_id": "eth",
                "token": "0x123",
                "min_balance": 100.0,
                "verifier": "0x456"
            }
        }

        # Save using verification module functions
        result = save_json_file(CONFIG_PATH, test_config)
        assert result == True, "Failed to save config in file mode"
        print("✅ Config saved in file mode")

        # Load using verification module functions
        loaded_config = load_json_file(CONFIG_PATH)
        assert loaded_config == test_config, "Failed to load config in file mode"
        print("✅ Config loaded in file mode")

        # Test 3: Test WITH DATABASE_URL (database mode)
        print("\n3️⃣ Testing database mode (DATABASE_URL set)...")
        os.environ["DATABASE_URL"] = "sqlite:///test_verification.db"

        # Reload module to pick up DATABASE_URL
        import importlib
        import verification as ver_module
        importlib.reload(ver_module)

        from verification import (
            load_json_file as db_load,
            save_json_file as db_save,
            is_group_blocked, track_rejection,
            get_rejection_count, reset_rejection_count,
            CONFIG_PATH, USER_DATA_PATH, REJECTED_GROUPS_PATH
        )

        # Save in database mode
        db_config = {
            "group2": {
                "chain_id": "bsc",
                "token": "0x789",
                "min_balance": 200.0,
                "verifier": "0xabc"
            }
        }

        result = db_save(CONFIG_PATH, db_config)
        assert result == True, "Failed to save config in database mode"
        print("✅ Config saved in database mode")

        # Load in database mode
        loaded_db_config = db_load(CONFIG_PATH)
        assert loaded_db_config == db_config, "Failed to load config in database mode"
        print("✅ Config loaded in database mode")

        # Test 4: Test 3-strike system with database
        print("\n4️⃣ Testing 3-strike system with database...")

        test_group_id = "-1001234567890"
        test_group_name = "Test Group"

        # Initial state
        assert get_rejection_count(test_group_id) == 0, "Initial rejection count should be 0"
        assert not is_group_blocked(test_group_id), "Group should not be blocked initially"
        print("✅ Initial state correct")

        # First rejection
        is_blocked = track_rejection(test_group_id, test_group_name)
        assert not is_blocked, "Group should not be blocked after 1 rejection"
        assert get_rejection_count(test_group_id) == 1, "Rejection count should be 1"
        print("✅ First rejection tracked correctly")

        # Second rejection
        is_blocked = track_rejection(test_group_id, test_group_name)
        assert not is_blocked, "Group should not be blocked after 2 rejections"
        assert get_rejection_count(test_group_id) == 2, "Rejection count should be 2"
        print("✅ Second rejection tracked correctly")

        # Third rejection (should block)
        is_blocked = track_rejection(test_group_id, test_group_name)
        assert is_blocked, "Group should be blocked after 3 rejections"
        assert get_rejection_count(test_group_id) == 3, "Rejection count should be 3"
        assert is_group_blocked(test_group_id), "Group should be blocked"
        print("✅ Third rejection blocks group correctly")

        # Reset
        result = reset_rejection_count(test_group_id)
        assert result == True, "Reset should succeed"
        assert get_rejection_count(test_group_id) == 0, "Rejection count should be 0 after reset"
        assert not is_group_blocked(test_group_id), "Group should not be blocked after reset"
        print("✅ Reset works correctly")

        # Test 5: Test data persistence
        print("\n5️⃣ Testing data persistence...")

        # Save some data
        persistence_data = {
            "persistent_group": {
                "chain_id": "polygon",
                "token": "0xdef",
                "min_balance": 500.0,
                "verifier": "0x999"
            }
        }

        db_save(CONFIG_PATH, persistence_data)
        print("✅ Data saved")

        # Reload module (simulates service restart)
        importlib.reload(ver_module)
        from verification import load_json_file as reload_load

        # Load data after reload
        reloaded_data = reload_load(CONFIG_PATH)
        assert reloaded_data == persistence_data, "Data should persist after reload"
        print("✅ Data persists after module reload")

        # Test 6: Test user data storage
        print("\n6️⃣ Testing user data storage...")

        user_data = {
            "group1": {
                "user1": {
                    "address": "0xabc123",
                    "verified": True,
                    "last_verified": 1234567890
                },
                "user2": {
                    "address": "0xdef456",
                    "verified": False,
                    "last_verified": None
                }
            }
        }

        db_save(USER_DATA_PATH, user_data)
        loaded_user_data = reload_load(USER_DATA_PATH)
        assert loaded_user_data == user_data, "User data should be stored correctly"
        print("✅ User data stored and loaded correctly")

        # Test 7: Test rejected groups storage
        print("\n7️⃣ Testing rejected groups storage...")

        rejected_data = db_load(REJECTED_GROUPS_PATH)
        assert test_group_id in rejected_data, "Rejected groups should be in storage"
        print("✅ Rejected groups stored correctly")

        print("\n🎉 ALL VERIFICATION INTEGRATION TESTS PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        os.chdir(original_dir)
        shutil.rmtree(test_dir, ignore_errors=True)
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

if __name__ == "__main__":
    success = test_verification_integration()
    sys.exit(0 if success else 1)
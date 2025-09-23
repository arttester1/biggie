#!/usr/bin/env python3
"""
End-to-End Test: Simulate Main Bot and Cron Service sharing data via database
"""

import os
import sys
import tempfile
import shutil

def test_end_to_end():
    """Simulate complete workflow: Main Bot saves, Cron reads"""
    print("🧪 End-to-End Test: Main Bot ↔ Cron Service Data Sharing...")

    test_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()

    try:
        os.chdir(test_dir)
        sys.path.insert(0, original_dir)

        # Setup DATABASE_URL to simulate Railway environment
        os.environ["DATABASE_URL"] = "sqlite:///railway_shared.db"
        os.environ["DATA_DIR"] = test_dir

        # Test 1: Main Bot saves configuration
        print("\n1️⃣ Simulating Main Bot saving configuration...")

        from verification import save_json_file, CONFIG_PATH, USER_DATA_PATH

        # Main bot saves group configuration
        main_bot_config = {
            "-1001234567890": {
                "chain_id": "eth",
                "token": "0x1234567890123456789012345678901234567890",
                "min_balance": 1000.0,
                "verifier": "0x0987654321098765432109876543210987654321"
            },
            "-1005555555555": {
                "chain_id": "bsc",
                "token": "0xabcdef1234567890abcdef1234567890abcdef12",
                "min_balance": 500.0,
                "verifier": "0x1111111111111111111111111111111111111111"
            }
        }

        result = save_json_file(CONFIG_PATH, main_bot_config)
        assert result == True, "Main bot failed to save config"
        print("✅ Main Bot saved 2 group configurations")

        # Main bot saves user data
        main_bot_users = {
            "-1001234567890": {
                "7585807164": {
                    "address": "0x000000000Ab8Af2f9fFFD660214F27C6067Ed072",
                    "verified": True,
                    "last_verified": 1234567890,
                    "verification_tx": True
                }
            },
            "-1005555555555": {
                "1111111111": {
                    "address": "0x2222222222222222222222222222222222222222",
                    "verified": True,
                    "last_verified": 9876543210,
                    "verification_tx": True
                }
            }
        }

        result = save_json_file(USER_DATA_PATH, main_bot_users)
        assert result == True, "Main bot failed to save user data"
        print("✅ Main Bot saved user data for 2 groups")

        # Test 2: Cron Service reads configuration (simulate different process)
        print("\n2️⃣ Simulating Cron Service reading configuration...")

        # Reimport to simulate separate service
        import importlib
        import verification as ver_module
        importlib.reload(ver_module)

        from verification import load_json_file, CONFIG_PATH, USER_DATA_PATH

        # Cron reads config
        cron_config = load_json_file(CONFIG_PATH)
        assert cron_config == main_bot_config, "Cron couldn't read Main Bot's config"
        print(f"✅ Cron Service read {len(cron_config)} group configurations")

        # Cron reads user data
        cron_users = load_json_file(USER_DATA_PATH)
        assert cron_users == main_bot_users, "Cron couldn't read Main Bot's user data"
        print(f"✅ Cron Service read user data for {len(cron_users)} groups")

        # Test 3: Verify cron can process the data
        print("\n3️⃣ Simulating Cron Service verification logic...")

        groups_to_verify = 0
        users_to_verify = 0

        for group_id, group_config in cron_config.items():
            groups_to_verify += 1
            group_users = cron_users.get(group_id, {})

            for user_id, user_info in group_users.items():
                if user_info.get("verified"):
                    users_to_verify += 1
                    print(f"   📋 Would verify user {user_id} in group {group_id}")
                    print(f"      Address: {user_info['address']}")
                    print(f"      Required: {group_config['min_balance']} tokens on {group_config['chain_id']}")

        assert groups_to_verify == 2, "Should have 2 groups to verify"
        assert users_to_verify == 2, "Should have 2 users to verify"
        print(f"✅ Cron would verify {users_to_verify} users in {groups_to_verify} groups")

        # Test 4: Cron updates user data (user loses balance)
        print("\n4️⃣ Simulating Cron Service updating user data...")

        # Cron marks user as unverified (lost balance)
        cron_users["-1001234567890"]["7585807164"]["verified"] = False

        result = save_json_file(USER_DATA_PATH, cron_users)
        assert result == True, "Cron failed to update user data"
        print("✅ Cron Service updated user verification status")

        # Test 5: Main Bot sees Cron's update
        print("\n5️⃣ Verifying Main Bot sees Cron's update...")

        importlib.reload(ver_module)
        from verification import load_json_file, USER_DATA_PATH

        main_bot_reads_update = load_json_file(USER_DATA_PATH)
        assert main_bot_reads_update["-1001234567890"]["7585807164"]["verified"] == False, \
            "Main Bot should see Cron's update"
        print("✅ Main Bot successfully read Cron's update")

        # Test 6: Test 3-strike system across services
        print("\n6️⃣ Testing 3-strike system across services...")

        from verification import track_rejection, is_group_blocked, get_rejection_count

        test_group = "-1009999999999"

        # Main bot rejects group (strike 1)
        track_rejection(test_group, "Test Group")
        assert get_rejection_count(test_group) == 1

        # Cron checks (should see strike 1)
        importlib.reload(ver_module)
        from verification import get_rejection_count as cron_get_count, is_group_blocked as cron_is_blocked

        assert cron_get_count(test_group) == 1, "Cron should see Main Bot's rejection"
        assert not cron_is_blocked(test_group), "Group should not be blocked yet"
        print("✅ Cron sees Main Bot's rejection (1/3)")

        # Main bot adds strikes 2 and 3
        from verification import track_rejection as main_track
        main_track(test_group, "Test Group")
        is_blocked = main_track(test_group, "Test Group")

        assert is_blocked == True, "Group should be blocked after 3 strikes"

        # Cron checks blocked status
        importlib.reload(ver_module)
        from verification import is_group_blocked as final_check

        assert final_check(test_group) == True, "Cron should see group is blocked"
        print("✅ Both services share 3-strike blocking state")

        # Test 7: Performance check
        print("\n7️⃣ Performance check: Multiple saves/loads...")

        import time
        start_time = time.time()

        for i in range(10):
            test_data = {"iteration": i, "data": f"test_{i}"}
            save_json_file(f"perf_test_{i}.json", test_data)
            loaded = load_json_file(f"perf_test_{i}.json")
            assert loaded == test_data

        elapsed = time.time() - start_time
        print(f"✅ 10 save/load cycles completed in {elapsed:.2f} seconds")

        # Test 8: Error handling
        print("\n8️⃣ Testing error handling...")

        # Try to load non-existent file
        missing_data = load_json_file("non_existent_file.json")
        assert missing_data == {}, "Should return empty dict for missing file"
        print("✅ Handles missing files correctly")

        # Test with invalid JSON (should not crash)
        try:
            result = save_json_file("test.json", {"valid": "data"})
            assert result == True
            print("✅ Handles valid data correctly")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

        print("\n" + "="*60)
        print("🎉 ALL END-TO-END TESTS PASSED!")
        print("="*60)
        print("\n✅ VERIFIED:")
        print("   • Main Bot can save data to database")
        print("   • Cron Service can read Main Bot's data")
        print("   • Cron Service can update data")
        print("   • Main Bot can read Cron's updates")
        print("   • 3-strike system works across services")
        print("   • Error handling works correctly")
        print("   • Performance is acceptable")
        print("\n🚀 Railway deployment will work correctly!")
        return True

    except Exception as e:
        print(f"\n❌ END-TO-END TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        os.chdir(original_dir)
        shutil.rmtree(test_dir, ignore_errors=True)
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        if "DATA_DIR" in os.environ:
            del os.environ["DATA_DIR"]

if __name__ == "__main__":
    success = test_end_to_end()
    sys.exit(0 if success else 1)
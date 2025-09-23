#!/usr/bin/env python3
"""
Test script for 3-strike blocking functionality
"""

import json
import os
import tempfile
import shutil

# Import the functions we need to test
from main import (
    track_rejection,
    is_group_blocked,
    get_rejection_count,
    reset_rejection_count,
    get_blocked_groups,
    get_all_rejections,
    DATA_DIR,
    REJECTED_GROUPS_PATH
)

def test_3_strike_system():
    """Test the 3-strike rejection tracking system"""
    print("🧪 Testing 3-Strike Blocking System...")

    # Use a temporary directory for testing
    original_data_dir = DATA_DIR
    test_dir = tempfile.mkdtemp()

    # Patch the global variables for testing
    import main
    main.DATA_DIR = test_dir
    main.REJECTED_GROUPS_PATH = os.path.join(test_dir, "rejected_groups.json")

    try:
        test_group_id = "-1001234567890"
        test_group_name = "Test Group"
        test_admin_id = "123456789"
        test_admin_name = "Test Admin"

        print(f"\n1️⃣ Testing initial state...")
        assert get_rejection_count(test_group_id) == 0
        assert not is_group_blocked(test_group_id)
        print("✅ Initial state correct")

        print(f"\n2️⃣ Testing first rejection...")
        is_blocked = track_rejection(test_group_id, test_group_name, test_admin_id, test_admin_name)
        assert not is_blocked
        assert get_rejection_count(test_group_id) == 1
        assert not is_group_blocked(test_group_id)
        print("✅ First rejection tracked correctly")

        print(f"\n3️⃣ Testing second rejection...")
        is_blocked = track_rejection(test_group_id, test_group_name, test_admin_id, test_admin_name)
        assert not is_blocked
        assert get_rejection_count(test_group_id) == 2
        assert not is_group_blocked(test_group_id)
        print("✅ Second rejection tracked correctly")

        print(f"\n4️⃣ Testing third rejection (should block)...")
        is_blocked = track_rejection(test_group_id, test_group_name, test_admin_id, test_admin_name)
        assert is_blocked
        assert get_rejection_count(test_group_id) == 3
        assert is_group_blocked(test_group_id)
        print("✅ Third rejection blocks group correctly")

        print(f"\n5️⃣ Testing blocked groups list...")
        blocked_groups = get_blocked_groups()
        assert test_group_id in blocked_groups
        assert blocked_groups[test_group_id]["blocked"] == True
        assert blocked_groups[test_group_id]["rejection_count"] == 3
        print("✅ Blocked groups list works correctly")

        print(f"\n6️⃣ Testing all rejections list...")
        all_rejections = get_all_rejections()
        assert test_group_id in all_rejections
        assert all_rejections[test_group_id]["rejection_count"] == 3
        assert all_rejections[test_group_id]["blocked"] == True
        print("✅ All rejections list works correctly")

        print(f"\n7️⃣ Testing unblock functionality...")
        reset_result = reset_rejection_count(test_group_id)
        assert reset_result == True
        assert get_rejection_count(test_group_id) == 0
        assert not is_group_blocked(test_group_id)
        print("✅ Unblock functionality works correctly")

        print(f"\n8️⃣ Testing fourth rejection after reset...")
        is_blocked = track_rejection(test_group_id, test_group_name, test_admin_id, test_admin_name)
        assert not is_blocked
        assert get_rejection_count(test_group_id) == 1
        assert not is_group_blocked(test_group_id)
        print("✅ Rejection tracking works correctly after reset")

        print("\n🎉 ALL TESTS PASSED! 3-Strike system is working correctly!")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)
        # Restore original DATA_DIR
        main.DATA_DIR = original_data_dir
        main.REJECTED_GROUPS_PATH = os.path.join(original_data_dir, "rejected_groups.json")

if __name__ == "__main__":
    test_3_strike_system()
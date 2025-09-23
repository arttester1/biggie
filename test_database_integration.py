#!/usr/bin/env python3
"""
Comprehensive test for database integration
Tests PostgreSQL adapter with SQLite fallback
"""

import os
import sys
import json
import tempfile
import shutil

def test_database_simple():
    """Test database_simple.py functionality"""
    print("🧪 Testing Database Integration...")

    # Create temporary directory for testing
    test_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()

    try:
        os.chdir(test_dir)

        # Test 1: Import and basic functionality
        print("\n1️⃣ Testing database_simple import...")
        sys.path.insert(0, original_dir)
        from database_simple import load_json_file, save_json_file, migrate_files_to_database
        print("✅ Import successful")

        # Test 2: Test WITHOUT DATABASE_URL (file fallback)
        print("\n2️⃣ Testing file fallback (no DATABASE_URL)...")
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        test_data = {
            "group1": {
                "chain_id": "eth",
                "token": "0x123",
                "min_balance": 100.0,
                "verifier": "0x456"
            }
        }

        test_file = os.path.join(test_dir, "test_config.json")

        # Save to file
        result = save_json_file(test_file, test_data)
        assert result == True, "Save to file failed"
        print("✅ Save to file successful")

        # Load from file
        loaded_data = load_json_file(test_file)
        assert loaded_data == test_data, "Load from file failed"
        print("✅ Load from file successful")
        print(f"   Loaded data: {json.dumps(loaded_data, indent=2)}")

        # Test 3: Test WITH DATABASE_URL (SQLite fallback)
        print("\n3️⃣ Testing SQLite database (DATABASE_URL set)...")

        # Set DATABASE_URL to trigger database mode (will fallback to SQLite)
        os.environ["DATABASE_URL"] = "sqlite:///test.db"

        # Need to reimport to pick up new environment variable
        import importlib
        import database_simple as db_module
        importlib.reload(db_module)
        from database_simple import load_json_file as db_load, save_json_file as db_save

        # Save to database
        test_data_db = {
            "group2": {
                "chain_id": "bsc",
                "token": "0x789",
                "min_balance": 200.0,
                "verifier": "0xabc"
            }
        }

        db_file_path = os.path.join(test_dir, "db_config.json")
        result = db_save(db_file_path, test_data_db)
        assert result == True, "Save to database failed"
        print("✅ Save to database successful")

        # Load from database
        loaded_db_data = db_load(db_file_path)
        assert loaded_db_data == test_data_db, "Load from database failed"
        print("✅ Load from database successful")
        print(f"   Loaded data: {json.dumps(loaded_db_data, indent=2)}")

        # Test 4: Test all JSON file types
        print("\n4️⃣ Testing all JSON file types...")

        test_files = {
            "config.json": {"group1": {"chain_id": "eth", "token": "0x123", "min_balance": 100.0, "verifier": "0x456"}},
            "user_data.json": {"group1": {"user1": {"address": "0xabc", "verified": True}}},
            "whitelist.json": {"group1": True, "group2": True},
            "pending_whitelist.json": {"group3": {"group_name": "Test", "admin_id": "123", "admin_name": "Admin", "timestamp": 123456}},
            "rejected_groups.json": {"group4": {"rejection_count": 2, "blocked": False}},
            "verification_links.json": {"token123": "group1"}
        }

        for filename, data in test_files.items():
            filepath = os.path.join(test_dir, filename)

            # Save
            result = db_save(filepath, data)
            assert result == True, f"Failed to save {filename}"

            # Load
            loaded = db_load(filepath)
            assert loaded == data, f"Failed to load {filename} correctly"
            print(f"   ✅ {filename} works correctly")

        print("✅ All file types work correctly")

        # Test 5: Test migration script
        print("\n5️⃣ Testing migration from files to database...")

        # First, clear DATABASE_URL to create files
        del os.environ["DATABASE_URL"]
        importlib.reload(db_module)
        from database_simple import load_json_file as file_load, save_json_file as file_save

        # Create some test files
        os.makedirs(test_dir, exist_ok=True)
        os.environ["DATA_DIR"] = test_dir

        migration_data = {
            "config.json": {"migration_test": {"data": "test"}},
            "user_data.json": {"migration_user": {"verified": True}}
        }

        for filename, data in migration_data.items():
            filepath = os.path.join(test_dir, filename)
            with open(filepath, "w") as f:
                json.dump(data, f)

        # Now set DATABASE_URL and run migration
        os.environ["DATABASE_URL"] = "sqlite:///migration_test.db"
        importlib.reload(db_module)

        # Import migration function
        from database_simple import migrate_files_to_database

        # Run migration
        migrate_files_to_database()

        # Verify data was migrated
        from database_simple import load_json_file as migrated_load

        for filename, expected_data in migration_data.items():
            filepath = os.path.join(test_dir, filename)
            loaded = migrated_load(filepath)
            assert loaded == expected_data, f"Migration failed for {filename}"
            print(f"   ✅ {filename} migrated successfully")

        print("✅ Migration works correctly")

        # Test 6: Test concurrent access (simulate two services)
        print("\n6️⃣ Testing concurrent access (simulating two services)...")

        # Service 1 writes
        service1_data = {"service1_group": {"token": "0x111"}}
        filepath = os.path.join(test_dir, "shared_config.json")
        db_save(filepath, service1_data)
        print("   ✅ Service 1 wrote data")

        # Service 2 reads (simulated by new load)
        service2_read = db_load(filepath)
        assert service2_read == service1_data, "Service 2 couldn't read Service 1's data"
        print("   ✅ Service 2 read Service 1's data successfully")

        # Service 2 updates
        service2_data = {**service1_data, "service2_group": {"token": "0x222"}}
        db_save(filepath, service2_data)
        print("   ✅ Service 2 updated data")

        # Service 1 reads updated data
        service1_read = db_load(filepath)
        assert service1_read == service2_data, "Service 1 couldn't read Service 2's updates"
        print("   ✅ Service 1 read Service 2's updates successfully")

        print("✅ Concurrent access works correctly")

        print("\n🎉 ALL DATABASE TESTS PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        os.chdir(original_dir)
        shutil.rmtree(test_dir, ignore_errors=True)
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        if "DATA_DIR" in os.environ:
            del os.environ["DATA_DIR"]

if __name__ == "__main__":
    success = test_database_simple()
    sys.exit(0 if success else 1)
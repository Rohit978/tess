
import sys
import os
import shutil

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.core.vault_manager import VaultManager

def test_vault():
    print("Testing VaultManager...")
    
    # Setup test env (backup existing key if any)
    vm = VaultManager()
    
    # Store
    print("Storing secret 'test_key'...")
    res = vm.store_secret("test_key", "super_secret_value")
    print(res)
    
    # Get
    print("Retrieving secret 'test_key'...")
    val = vm.get_secret("test_key")
    print(f"Value: {val}")
    assert val == "super_secret_value"
    
    # List
    print("Listing secrets...")
    keys = vm.list_secrets()
    print(f"Keys: {keys}")
    assert "test_key" in keys
    
    # Delete
    print("Deleting secret 'test_key'...")
    res_del = vm.delete_secret("test_key")
    print(res_del)
    
    # Verify Deletion
    assert vm.get_secret("test_key") is None
    print("✅ VaultManager Secure Storage Verified.")

if __name__ == "__main__":
    test_vault()

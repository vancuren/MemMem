#!/usr/bin/env python3
"""Test script for tenant deployment"""

import subprocess
import sys
import json
from pathlib import Path

def test_tenant_creation():
    print("🧪 Testing tenant creation...")
    
    try:
        # Test creating a tenant
        result = subprocess.run([
            "python3", "scripts/manage-tenants.py", "create", "test-tenant", 
            "--domain", "test.local"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ Tenant creation successful!")
            tenant_info = json.loads(result.stdout)
            print(f"Tenant ID: {tenant_info['tenant_id']}")
            print(f"Domain: {tenant_info['domain']}")
            print(f"API Key: {tenant_info['api_key'][:10]}...")
            
            # Test listing tenants
            list_result = subprocess.run([
                "python3", "scripts/manage-tenants.py", "list"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            if list_result.returncode == 0:
                tenants = json.loads(list_result.stdout)
                print(f"✅ Found {len(tenants)} tenant(s)")
                
                # Clean up - delete the test tenant
                delete_result = subprocess.run([
                    "python3", "scripts/manage-tenants.py", "delete", "test-tenant", "--force"
                ], capture_output=True, text=True, cwd=Path(__file__).parent)
                
                if delete_result.returncode == 0:
                    print("✅ Cleanup successful!")
                else:
                    print(f"⚠️ Cleanup failed: {delete_result.stderr}")
            else:
                print(f"❌ Failed to list tenants: {list_result.stderr}")
        else:
            print(f"❌ Tenant creation failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")

if __name__ == "__main__":
    test_tenant_creation()
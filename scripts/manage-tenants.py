#!/usr/bin/env python3
"""
Tenant management script for MemoryBank multi-tenant deployment
Provides API endpoints and CLI for managing tenant lifecycle
"""

import os
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sqlite3
import hashlib
import secrets

class TenantManager:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.path.dirname(os.path.dirname(__file__)))
        self.deployments_dir = self.project_root / "deployments"
        self.db_path = self.project_root / "tenant_management.db"
        self.init_database()
    
    def init_database(self):
        """Initialize tenant management database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id TEXT PRIMARY KEY,
                    api_key_hash TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    container_port INTEGER,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP,
                    metadata TEXT  -- JSON blob for additional data
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    request_count INTEGER DEFAULT 1,
                    FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
                )
            """)
    
    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        return f"mb_{secrets.token_urlsafe(32)}"
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def create_tenant(self, tenant_id: str, domain: str = "yourdomain.com", 
                     api_key: str = None) -> Dict:
        """Create a new tenant deployment"""
        if not tenant_id.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Tenant ID must contain only alphanumeric characters, hyphens, and underscores")
        
        # Check if tenant already exists
        if self.get_tenant(tenant_id):
            raise ValueError(f"Tenant {tenant_id} already exists")
        
        api_key = api_key or self.generate_api_key()
        api_key_hash = self.hash_api_key(api_key)
        
        # Deploy using shell script
        script_path = self.project_root / "scripts" / "deploy-tenant.sh"
        try:
            result = subprocess.run([
                str(script_path), tenant_id, api_key, domain
            ], capture_output=True, text=True)
            
            # Check if deployment actually failed (non-zero exit code)
            if result.returncode != 0:
                raise RuntimeError(f"Deployment failed with exit code {result.returncode}: {result.stderr}")
            
            # Parse deployment info
            deployment_info_path = self.deployments_dir / tenant_id / "deployment-info.json"
            if deployment_info_path.exists():
                with open(deployment_info_path) as f:
                    deployment_info = json.load(f)
                container_port = deployment_info.get("container_port")
            else:
                container_port = None
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO tenants (tenant_id, api_key_hash, domain, container_port, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (tenant_id, api_key_hash, f"{tenant_id}.{domain}", container_port, 
                     json.dumps(deployment_info if 'deployment_info' in locals() else {})))
            
            return {
                "tenant_id": tenant_id,
                "api_key": api_key,  # Only returned on creation
                "domain": f"{tenant_id}.{domain}",
                "container_port": container_port,
                "status": "active",
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise RuntimeError(f"Deployment failed: {str(e)}")
    
    def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        """Get tenant information"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            result = conn.execute("""
                SELECT tenant_id, domain, container_port, status, created_at, last_accessed, metadata
                FROM tenants WHERE tenant_id = ?
            """, (tenant_id,)).fetchone()
            
            if result:
                tenant = dict(result)
                tenant['metadata'] = json.loads(tenant['metadata'] or '{}')
                return tenant
        return None
    
    def list_tenants(self) -> List[Dict]:
        """List all tenants"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            results = conn.execute("""
                SELECT tenant_id, domain, container_port, status, created_at, last_accessed
                FROM tenants ORDER BY created_at DESC
            """).fetchall()
            
            return [dict(row) for row in results]
    
    def delete_tenant(self, tenant_id: str, force: bool = False) -> bool:
        """Delete a tenant deployment"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant_dir = self.deployments_dir / tenant_id
        
        # Stop and remove containers
        if tenant_dir.exists():
            try:
                subprocess.run([
                    "docker-compose", "down", "-v"
                ], cwd=tenant_dir, check=True, capture_output=True)
                
                if force:
                    # Remove deployment directory
                    import shutil
                    shutil.rmtree(tenant_dir)
                    
            except subprocess.CalledProcessError as e:
                if not force:
                    raise RuntimeError(f"Failed to stop containers: {e.stderr}")
        
        # Remove from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tenant_usage WHERE tenant_id = ?", (tenant_id,))
            conn.execute("DELETE FROM tenants WHERE tenant_id = ?", (tenant_id,))
        
        return True
    
    def update_tenant_status(self, tenant_id: str, status: str):
        """Update tenant status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE tenants SET status = ?, last_accessed = CURRENT_TIMESTAMP
                WHERE tenant_id = ?
            """, (status, tenant_id))
    
    def get_tenant_stats(self, tenant_id: str = None) -> Dict:
        """Get usage statistics"""
        with sqlite3.connect(self.db_path) as conn:
            if tenant_id:
                # Stats for specific tenant
                result = conn.execute("""
                    SELECT COUNT(*) as total_requests,
                           COUNT(DISTINCT endpoint) as unique_endpoints,
                           MAX(timestamp) as last_request
                    FROM tenant_usage WHERE tenant_id = ?
                """, (tenant_id,)).fetchone()
                
                return {
                    "tenant_id": tenant_id,
                    "total_requests": result[0],
                    "unique_endpoints": result[1],
                    "last_request": result[2]
                }
            else:
                # Overall stats
                result = conn.execute("""
                    SELECT COUNT(DISTINCT tenant_id) as total_tenants,
                           COUNT(*) as total_requests,
                           COUNT(DISTINCT endpoint) as unique_endpoints
                    FROM tenant_usage tu
                    JOIN tenants t ON tu.tenant_id = t.tenant_id
                    WHERE t.status = 'active'
                """).fetchone()
                
                return {
                    "total_tenants": result[0],
                    "total_requests": result[1],
                    "unique_endpoints": result[2]
                }

def main():
    parser = argparse.ArgumentParser(description="MemoryBank Tenant Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create tenant
    create_parser = subparsers.add_parser("create", help="Create new tenant")
    create_parser.add_argument("tenant_id", help="Unique tenant identifier")
    create_parser.add_argument("--domain", default="yourdomain.com", help="Base domain")
    create_parser.add_argument("--api-key", help="Custom API key (optional)")
    
    # List tenants
    list_parser = subparsers.add_parser("list", help="List all tenants")
    
    # Get tenant info
    info_parser = subparsers.add_parser("info", help="Get tenant information")
    info_parser.add_argument("tenant_id", help="Tenant identifier")
    
    # Delete tenant
    delete_parser = subparsers.add_parser("delete", help="Delete tenant")
    delete_parser.add_argument("tenant_id", help="Tenant identifier")
    delete_parser.add_argument("--force", action="store_true", help="Force delete (remove all data)")
    
    # Stats
    stats_parser = subparsers.add_parser("stats", help="Get usage statistics")
    stats_parser.add_argument("--tenant-id", help="Get stats for specific tenant")
    
    args = parser.parse_args()
    manager = TenantManager()
    
    try:
        if args.command == "create":
            result = manager.create_tenant(args.tenant_id, args.domain, args.api_key)
            print(json.dumps(result, indent=2))
            
        elif args.command == "list":
            tenants = manager.list_tenants()
            print(json.dumps(tenants, indent=2))
            
        elif args.command == "info":
            tenant = manager.get_tenant(args.tenant_id)
            if tenant:
                print(json.dumps(tenant, indent=2))
            else:
                print(f"Tenant {args.tenant_id} not found")
                
        elif args.command == "delete":
            success = manager.delete_tenant(args.tenant_id, args.force)
            if success:
                print(f"Tenant {args.tenant_id} deleted successfully")
            else:
                print(f"Tenant {args.tenant_id} not found")
                
        elif args.command == "stats":
            stats = manager.get_tenant_stats(args.tenant_id)
            print(json.dumps(stats, indent=2))
            
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
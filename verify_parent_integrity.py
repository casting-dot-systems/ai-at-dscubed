#!/usr/bin/env python3
"""
Verify parent component integrity in silver.internal_msg_component table.
This script ensures all parent_component_id values reference existing component_id values.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def load_database_engine():
    """Load database engine from environment variables."""
    project_root = Path(__file__).parent
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not set in environment variables")
    
    return create_engine(database_url)

def verify_parent_integrity():
    """Verify parent component integrity."""
    engine = load_database_engine()
    
    print("🔍 Verifying parent component integrity...")
    print("=" * 50)
    
    with engine.connect() as conn:
        # Count total records
        total_query = "SELECT COUNT(*) as total FROM silver.internal_msg_component;"
        total_count = conn.execute(text(total_query)).fetchone().total
        
        # Count orphaned references
        orphaned_query = """
        SELECT COUNT(*) as orphaned_count
        FROM silver.internal_msg_component 
        WHERE parent_component_id IS NOT NULL 
        AND parent_component_id NOT IN (
            SELECT component_id FROM silver.internal_msg_component
        );
        """
        orphaned_count = conn.execute(text(orphaned_query)).fetchone().orphaned_count
        
        # Count valid parent relationships
        valid_query = """
        SELECT COUNT(*) as valid_count
        FROM silver.internal_msg_component 
        WHERE parent_component_id IS NOT NULL 
        AND parent_component_id IN (
            SELECT component_id FROM silver.internal_msg_component
        );
        """
        valid_count = conn.execute(text(valid_query)).fetchone().valid_count
        
        # Count root components (no parent)
        root_query = """
        SELECT COUNT(*) as root_count
        FROM silver.internal_msg_component 
        WHERE parent_component_id IS NULL;
        """
        root_count = conn.execute(text(root_query)).fetchone().root_count
        
        # Check for circular references
        circular_query = """
        SELECT COUNT(*) as circular_count
        FROM silver.internal_msg_component 
        WHERE parent_component_id = component_id;
        """
        circular_count = conn.execute(text(circular_query)).fetchone().circular_count
        
        print(f"📊 Component Statistics:")
        print(f"   Total components: {total_count}")
        print(f"   Root components (no parent): {root_count}")
        print(f"   Valid parent relationships: {valid_count}")
        print(f"   Orphaned parent references: {orphaned_count}")
        print(f"   Circular references: {circular_count}")
        
        print(f"\n🔍 Integrity Checks:")
        
        # Check 1: No orphaned references
        if orphaned_count == 0:
            print("   ✅ No orphaned parent references")
        else:
            print(f"   ❌ {orphaned_count} orphaned parent references found")
        
        # Check 2: No circular references
        if circular_count == 0:
            print("   ✅ No circular references")
        else:
            print(f"   ❌ {circular_count} circular references found")
        
        # Check 3: Total count consistency
        if total_count == root_count + valid_count + orphaned_count:
            print("   ✅ Count consistency check passed")
        else:
            print("   ❌ Count consistency check failed")
        
        # Overall result
        integrity_passed = (orphaned_count == 0 and circular_count == 0)
        
        print(f"\n🎯 Overall Result:")
        if integrity_passed:
            print("   ✅ PARENT COMPONENT INTEGRITY CHECK PASSED!")
            print("   🎉 All parent_component_id values reference existing component_id values")
        else:
            print("   ❌ PARENT COMPONENT INTEGRITY CHECK FAILED!")
            print("   ⚠️  Some parent_component_id values don't reference existing component_id values")
        
        return integrity_passed

if __name__ == "__main__":
    try:
        verify_parent_integrity()
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        raise 
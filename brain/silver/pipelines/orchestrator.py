#!/usr/bin/env python3
"""
Silver Data Pipeline Orchestrator

This script runs all silver pipelines in the correct order:
1. Components (channels/forums/etc.)
2. Members (who can access which components)  
3. Messages (actual message content)
4. Conversations (grouping related messages)
5. Conversation Members (who participated in conversations)
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_pipeline(script_name: str, description: str) -> bool:
    """Run a pipeline script and return success status."""
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"⚠️  Pipeline script not found: {script_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"🚀 Running: {description}")
    print(f"   Script: {script_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)], 
            capture_output=True, 
            text=True,
            cwd=Path(__file__).parent
        )
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully!")
            return True
        else:
            print(f"❌ {description} failed with return code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running {description}: {str(e)}")
        return False

def main():
    """Run all silver pipelines in dependency order."""
    print("🎯 Starting Silver Data Pipeline Orchestration")
    print("=" * 60)
    
    pipelines = [
        {
            "script": "populate_channel_meta_simple.py",
            "description": "Component Metadata (Channels/Forums)",
            "required": True
        },
        {
            "script": "populate_component_members.py", 
            "description": "Component Member Relationships",
            "required": False  # Optional since it creates synthetic data
        },
        {
            "script": "populate_channel_messages_simple.py",
            "description": "Message Content", 
            "required": True
        }
    ]
    
    successful_pipelines = []
    failed_pipelines = []
    
    for pipeline in pipelines:
        success = run_pipeline(pipeline["script"], pipeline["description"])
        
        if success:
            successful_pipelines.append(pipeline["description"])
        else:
            failed_pipelines.append(pipeline["description"])
            
            if pipeline["required"]:
                print(f"\n❌ CRITICAL FAILURE: {pipeline['description']} is required but failed.")
                print("   Stopping orchestration.")
                break
            else:
                print(f"\n⚠️  OPTIONAL FAILURE: {pipeline['description']} failed but is not required.")
                print("   Continuing with remaining pipelines.")
    
    # Final summary
    print(f"\n{'='*60}")
    print("📊 ORCHESTRATION SUMMARY")
    print(f"{'='*60}")
    
    if successful_pipelines:
        print(f"✅ Successful ({len(successful_pipelines)}):")
        for pipeline in successful_pipelines:
            print(f"   - {pipeline}")
    
    if failed_pipelines:
        print(f"\n❌ Failed ({len(failed_pipelines)}):")
        for pipeline in failed_pipelines:
            print(f"   - {pipeline}")
    
    if not failed_pipelines:
        print("\n🎉 ALL PIPELINES COMPLETED SUCCESSFULLY!")
        print("   Your silver data layer is ready for use.")
    elif len(successful_pipelines) > 0:
        print(f"\n⚠️  PARTIAL SUCCESS: {len(successful_pipelines)} pipelines succeeded, {len(failed_pipelines)} failed.")
        print("   Check the logs above for error details.")
    else:
        print("\n💥 ALL PIPELINES FAILED!")
        print("   Please check your configuration and data sources.")
    
    return len(failed_pipelines) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

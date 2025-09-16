#!/usr/bin/env python3
"""
Bronze Pipelines Runner
=======================

This script runs all bronze layer data pipelines in the correct order.
It handles dependencies, error recovery, and provides comprehensive logging.

Pipeline Order:
1. Discord Channels (creates base channel structure)
2. Discord Relevant Channels (filters channels)
3. Discord Chats (messages - depends on channels)
4. Discord Reactions (depends on chats)
5. Notion Committee (independent)

Usage:
    python run_all_bronze_pipelines.py [options]

Options:
    --pipeline PIPELINE    Run only specific pipeline(s) (comma-separated)
    --skip-pipeline PIPELINE  Skip specific pipeline(s) (comma-separated)
    --validate-only        Only validate data extraction, don't load to DB
    --continue-on-error    Continue running other pipelines if one fails
    --dry-run             Show what would be run without executing
    --verbose             Enable verbose logging
    --help                Show this help message
"""

import argparse
import asyncio
import os
import sys
import time
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv


class PipelineRunner:
    """Manages execution of all bronze pipelines"""
    
    def __init__(self, verbose: bool = False, continue_on_error: bool = False):
        self.verbose = verbose
        self.continue_on_error = continue_on_error
        self.start_time = time.time()
        self.results = {}
        
        # Load environment variables
        load_dotenv()
        
        # Define pipeline configurations
        self.pipelines = {
            'discord_channels': {
                'name': 'Discord Channels',
                'script': 'discord_channel.py',
                'required_args': ['--input-path', 'dummy'],  # Required but not used
                'description': 'Extract Discord server channels and structure',
                'dependencies': []
            },
            'discord_relevant_channels': {
                'name': 'Discord Relevant Channels',
                'script': 'discord_relevant_channels.py',
                'required_args': ['--input-path', 'dummy'],
                'description': 'Filter and store relevant Discord channels',
                'dependencies': ['discord_channels']
            },
            'discord_chats': {
                'name': 'Discord Chats',
                'script': 'discord_chat.py',
                'required_args': ['--input-path', 'dummy'],
                'description': 'Extract Discord messages and chat history',
                'dependencies': ['discord_channels']
            },
            'discord_reactions': {
                'name': 'Discord Reactions',
                'script': 'discord_reaction.py',
                'required_args': ['--input-path', 'dummy'],
                'description': 'Extract Discord message reactions',
                'dependencies': ['discord_chats']
            },
            'notion_committee': {
                'name': 'Notion Committee',
                'script': 'notion_committee.py',
                'required_args': [],
                'description': 'Extract committee member data from Notion',
                'dependencies': []
            }
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def log_verbose(self, message: str):
        """Log verbose messages"""
        if self.verbose:
            self.log(message, "VERBOSE")
    
    def validate_environment(self, pipelines_to_run: List[str]) -> bool:
        """Validate that all required environment variables are set for the pipelines to run"""
        self.log("Validating environment variables...")
        
        # Determine which services are needed based on pipelines to run
        required_vars = {}
        
        if any(p in pipelines_to_run for p in ['discord_channels', 'discord_relevant_channels', 'discord_chats', 'discord_reactions']):
            required_vars['Discord'] = ['BOT_KEY', 'TEST_SERVER_ID']
        
        if 'notion_committee' in pipelines_to_run:
            required_vars['Notion'] = ['NOTION_API_KEY', 'NOTION_USERS_DATABASE_ID']
        
        missing_vars = []
        for service, vars_list in required_vars.items():
            for var in vars_list:
                if not os.getenv(var):
                    missing_vars.append(f"{service}: {var}")
        
        if missing_vars:
            self.log("❌ Missing required environment variables:", "ERROR")
            for var in missing_vars:
                self.log(f"  - {var}", "ERROR")
            self.log("Please set these variables in your .env file", "ERROR")
            return False
        
        self.log("✅ All required environment variables are set")
        return True
    
    def get_pipeline_execution_order(self, requested_pipelines: List[str]) -> List[str]:
        """Determine the correct execution order based on dependencies"""
        if not requested_pipelines:
            requested_pipelines = list(self.pipelines.keys())
        
        # Topological sort based on dependencies
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(pipeline):
            if pipeline in temp_visited:
                raise ValueError(f"Circular dependency detected involving {pipeline}")
            if pipeline in visited:
                return
            
            temp_visited.add(pipeline)
            
            # Visit dependencies first
            for dep in self.pipelines[pipeline]['dependencies']:
                if dep in requested_pipelines:
                    visit(dep)
            
            temp_visited.remove(pipeline)
            visited.add(pipeline)
            order.append(pipeline)
        
        for pipeline in requested_pipelines:
            if pipeline not in visited:
                visit(pipeline)
        
        return order
    
    def run_pipeline(self, pipeline_name: str, validate_only: bool = False) -> Dict[str, Any]:
        """Run a single pipeline"""
        if pipeline_name not in self.pipelines:
            raise ValueError(f"Unknown pipeline: {pipeline_name}")
        
        pipeline_config = self.pipelines[pipeline_name]
        script_path = Path(__file__).parent / pipeline_config['script']
        
        self.log(f"🚀 Starting {pipeline_config['name']} pipeline...")
        self.log(f"   Script: {script_path}")
        self.log(f"   Description: {pipeline_config['description']}")
        
        start_time = time.time()
        
        try:
            # Build command
            cmd = [sys.executable, str(script_path)]
            cmd.extend(pipeline_config['required_args'])
            
            if validate_only and pipeline_name == 'discord_reactions':
                cmd.extend(['--validate-only'])
            
            self.log_verbose(f"Command: {' '.join(cmd)}")
            
            # Change to the script directory to ensure proper imports
            original_cwd = os.getcwd()
            os.chdir(script_path.parent)
            
            try:
                # Run the pipeline
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per pipeline
                )
                
                if result.returncode == 0:
                    duration = time.time() - start_time
                    self.log(f"✅ {pipeline_config['name']} completed successfully in {duration:.2f}s")
                    
                    # Parse output for useful information
                    output_lines = result.stdout.strip().split('\n')
                    summary_info = {}
                    
                    for line in output_lines:
                        if 'Total' in line or 'extracted' in line or 'completed' in line:
                            summary_info['output'] = line
                    
                    return {
                        'success': True,
                        'duration': duration,
                        'output': result.stdout,
                        'summary': summary_info
                    }
                else:
                    duration = time.time() - start_time
                    self.log(f"❌ {pipeline_config['name']} failed after {duration:.2f}s", "ERROR")
                    self.log(f"Return code: {result.returncode}", "ERROR")
                    self.log(f"Error output: {result.stderr}", "ERROR")
                    
                    return {
                        'success': False,
                        'duration': duration,
                        'error': result.stderr,
                        'return_code': result.returncode
                    }
            
            finally:
                os.chdir(original_cwd)
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.log(f"⏰ {pipeline_config['name']} timed out after {duration:.2f}s", "ERROR")
            return {
                'success': False,
                'duration': duration,
                'error': 'Pipeline timed out (5 minute limit)'
            }
        except Exception as e:
            duration = time.time() - start_time
            self.log(f"💥 {pipeline_config['name']} crashed after {duration:.2f}s", "ERROR")
            self.log(f"Error: {str(e)}", "ERROR")
            if self.verbose:
                self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            
            return {
                'success': False,
                'duration': duration,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def run_all_pipelines(self, 
                         requested_pipelines: Optional[List[str]] = None,
                         skip_pipelines: Optional[List[str]] = None,
                         validate_only: bool = False,
                         dry_run: bool = False) -> Dict[str, Any]:
        """Run all pipelines in the correct order"""
        
        # Determine which pipelines to run
        if requested_pipelines:
            pipelines_to_run = requested_pipelines
        else:
            pipelines_to_run = list(self.pipelines.keys())
        
        # Remove skipped pipelines
        if skip_pipelines:
            pipelines_to_run = [p for p in pipelines_to_run if p not in skip_pipelines]
        
        # Validate pipeline names
        invalid_pipelines = [p for p in pipelines_to_run if p not in self.pipelines]
        if invalid_pipelines:
            raise ValueError(f"Unknown pipelines: {', '.join(invalid_pipelines)}")
        
        # Get execution order
        execution_order = self.get_pipeline_execution_order(pipelines_to_run)
        
        self.log("=" * 80)
        self.log("🏗️  BRONZE PIPELINES EXECUTION")
        self.log("=" * 80)
        self.log(f"Pipelines to run: {', '.join(execution_order)}")
        if validate_only:
            self.log("Mode: VALIDATION ONLY (no database writes)")
        if dry_run:
            self.log("Mode: DRY RUN (no actual execution)")
        
        if dry_run:
            self.log("\n📋 DRY RUN - Pipeline execution order:")
            for i, pipeline in enumerate(execution_order, 1):
                config = self.pipelines[pipeline]
                deps = ', '.join(config['dependencies']) if config['dependencies'] else 'none'
                self.log(f"  {i}. {config['name']} (depends on: {deps})")
            return {'success': True, 'dry_run': True}
        
        # Run pipelines
        successful_pipelines = []
        failed_pipelines = []
        
        for i, pipeline_name in enumerate(execution_order, 1):
            self.log(f"\n📦 [{i}/{len(execution_order)}] Running {pipeline_name}...")
            
            result = self.run_pipeline(pipeline_name, validate_only)
            self.results[pipeline_name] = result
            
            if result['success']:
                successful_pipelines.append(pipeline_name)
                if result.get('summary'):
                    self.log(f"   Summary: {result['summary']}")
            else:
                failed_pipelines.append(pipeline_name)
                if not self.continue_on_error:
                    self.log("❌ Stopping execution due to pipeline failure", "ERROR")
                    break
        
        # Summary
        total_duration = time.time() - self.start_time
        self.log("\n" + "=" * 80)
        self.log("📊 EXECUTION SUMMARY")
        self.log("=" * 80)
        self.log(f"Total execution time: {total_duration:.2f}s")
        self.log(f"Successful pipelines: {len(successful_pipelines)}")
        self.log(f"Failed pipelines: {len(failed_pipelines)}")
        
        if successful_pipelines:
            self.log(f"✅ Success: {', '.join(successful_pipelines)}")
        
        if failed_pipelines:
            self.log(f"❌ Failed: {', '.join(failed_pipelines)}", "ERROR")
        
        return {
            'success': len(failed_pipelines) == 0,
            'total_duration': total_duration,
            'successful_pipelines': successful_pipelines,
            'failed_pipelines': failed_pipelines,
            'results': self.results
        }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run all bronze data pipelines',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--pipeline',
        help='Run only specific pipeline(s) (comma-separated): discord_channels, discord_relevant_channels, discord_chats, discord_reactions, notion_committee'
    )
    
    parser.add_argument(
        '--skip-pipeline',
        help='Skip specific pipeline(s) (comma-separated)'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate data extraction, do not load to database'
    )
    
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue running other pipelines if one fails'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be run without executing'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Parse pipeline lists
    requested_pipelines = None
    if args.pipeline:
        requested_pipelines = [p.strip() for p in args.pipeline.split(',')]
    
    skip_pipelines = None
    if args.skip_pipeline:
        skip_pipelines = [p.strip() for p in args.skip_pipeline.split(',')]
    
    # Create runner and execute
    runner = PipelineRunner(
        verbose=args.verbose,
        continue_on_error=args.continue_on_error
    )
    
    try:
        # Determine which pipelines to run for validation
        if requested_pipelines:
            pipelines_for_validation = requested_pipelines
        else:
            pipelines_for_validation = list(runner.pipelines.keys())
        
        if skip_pipelines:
            pipelines_for_validation = [p for p in pipelines_for_validation if p not in skip_pipelines]
        
        # Validate environment
        if not runner.validate_environment(pipelines_for_validation):
            sys.exit(1)
        
        # Run pipelines
        result = runner.run_all_pipelines(
            requested_pipelines=requested_pipelines,
            skip_pipelines=skip_pipelines,
            validate_only=args.validate_only,
            dry_run=args.dry_run
        )
        
        if result['success']:
            runner.log("🎉 All bronze pipelines completed successfully!")
            sys.exit(0)
        else:
            runner.log("💥 Some pipelines failed. Check the logs above.", "ERROR")
            sys.exit(1)
            
    except KeyboardInterrupt:
        runner.log("⏹️  Execution interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        runner.log(f"💥 Unexpected error: {str(e)}", "ERROR")
        if args.verbose:
            runner.log(f"Traceback: {traceback.format_exc()}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    import subprocess  # Import here to avoid issues with path setup
    main()

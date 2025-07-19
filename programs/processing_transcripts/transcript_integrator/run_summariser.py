#!/usr/bin/env python3
"""
Enhanced Transcript Summariser Runner

This script runs the enhanced summariser that:
1. Downloads transcripts from Google Drive
2. Generates summaries using GPT-4.1
3. Updates meeting.sql with the summaries

Usage:
    python run_summariser.py
"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import the enhanced_summariser
sys.path.insert(0, os.path.dirname(__file__))

from enhanced_summariser import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 
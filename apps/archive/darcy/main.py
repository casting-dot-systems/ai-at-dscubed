#!/usr/bin/env python3
"""
Script to run the Discord bot in either production or development mode.

Usage:
    python run.py [--mode production|development]

    !!! Default mode is development !!!
"""

import argparse
import os
import shutil


def setup_environment(mode: str):
    """Set up the environment file based on the specified mode."""
    env_file = f".env.{mode}"
    if not os.path.exists(env_file):
        raise FileNotFoundError(f"Environment file {env_file} not found")

    # Copy the appropriate .env file to .env
    shutil.copy2(env_file, ".env")
    print(f"Using {mode} environment configuration")


def main():
    parser = argparse.ArgumentParser(description="Run the Discord bot")
    parser.add_argument(
        "--mode",
        choices=["production", "development"],
        default="development",
        help="Specify the environment mode (default: development)",
    )

    args = parser.parse_args()

    try:
        setup_environment(args.mode)

        # Run the bot using uv
        # TODO this is broken on my machine atm
        os.system("uv run programs/discord/bot.py")
        # running -m programs/discord/bot.py (as a module) doesn't work on my computer, add a comment if you need to use -m

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

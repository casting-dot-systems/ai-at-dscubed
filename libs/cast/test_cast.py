#!/usr/bin/env python3
"""Test script for the cast_ops library."""

import asyncio
import tempfile
from pathlib import Path

from cast_ops import (
    cast_create_note,
    cast_search_titles_fuzzy,
    cast_grep,
    cast_search_all,
    cast_read_note,
    cast_validate_note,
    cast_context_bundle,
)


async def test_cast_ops():
    """Basic test of cast_ops functionality."""
    print("Testing Cast Ops library...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = tmp_dir
        print(f"Testing in: {root}")

        # Test 1: Create a note
        print("\n1. Creating test note...")
        result = await cast_create_note(
            root=root,
            title="Test Note",
            content="This is a test note with some content.",
            frontmatter={"category": "test", "tags": ["demo"]},
            dependencies=["Another Note"]
        )
        print(f"Create result: {result}")

        # Test 2: Read the note
        print("\n2. Reading test note...")
        result = await cast_read_note(root, "Test Note")
        print(f"Read result: {result}")

        # Test 3: Search titles
        print("\n3. Searching by title...")
        result = await cast_search_titles_fuzzy(root, "test", limit=10)
        print(f"Title search result: {result}")

        # Test 4: Validate note
        print("\n4. Validating note...")
        result = await cast_validate_note(root, "Test Note")
        print(f"Validation result: {result}")

        # Test 5: Content bundle
        print("\n5. Getting context bundle...")
        result = await cast_context_bundle(root, "test", top_k=5)
        print(f"Context bundle result: {result}")

        print("\nAll tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_cast_ops())
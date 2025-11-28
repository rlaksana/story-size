#!/usr/bin/env python3
"""
Debug script to test the platform detection call
"""

import os
import asyncio
from story_size.config import load_config
from story_size.core.platform_ai_client import PlatformAwareAIClient
from story_size.core.code_analysis import analyze_all_platforms
from story_size.core.directory_resolver import DirectoryResolver
from story_size.core.docs import read_documents
from pathlib import Path

async def test_platform_detection():
    # Load config
    config = load_config(Path("sample_config.yml"))

    # Create client
    client = PlatformAwareAIClient(config)

    # Read test data
    doc_content = read_documents(Path("test_data/docs"))

    # Analyze platform directories
    resolver = DirectoryResolver()
    platform_dirs = resolver.resolve_platform_directories(
        fe_dir=Path("test_data/frontend"),
        be_dir=Path("test_data/backend"),
        mobile_dir=Path("test_data/mobile")
    )

    code_analysis = analyze_all_platforms(platform_dirs)

    try:
        # Test the exact platform detection call
        print("Testing platform detection...")
        result = await client.detect_platforms(doc_content, code_analysis)
        print("SUCCESS!")
        print("Result:", result)
    except Exception as e:
        print("ERROR:", e)

        # Let's try to see what prompt is being sent
        platform_structure = client._generate_platform_structure_analysis(code_analysis)
        print("\n--- PLATFORM STRUCTURE ---")
        print(platform_structure[:500])  # First 500 chars

        print("\n--- DOC SUMMARY ---")
        print(doc_content[:500])  # First 500 chars

if __name__ == "__main__":
    asyncio.run(test_platform_detection())
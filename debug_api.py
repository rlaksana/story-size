#!/usr/bin/env python3
"""
Debug script to test the AI API call
"""

import os
import asyncio
from story_size.config import load_config
from story_size.core.platform_ai_client import PlatformAwareAIClient
from pathlib import Path

async def test_api():
    # Load config
    config = load_config(Path("sample_config.yml"))

    # Create client
    client = PlatformAwareAIClient(config)

    # Simple test prompt
    test_prompt = """Analyze this work item and return JSON response:

{
  "platform_requirements": {
    "frontend": {"required": true, "scope": "high", "technologies": ["react"]},
    "backend": {"required": true, "scope": "high", "technologies": ["dotnet"]},
    "mobile": {"required": false, "scope": "low", "technologies": []},
    "devops": {"required": false, "scope": "low", "technologies": []}
  },
  "work_item_type": "feature",
  "complexity_level": "moderate",
  "estimated_platforms": ["frontend", "backend"],
  "confidence": 0.8,
  "reasoning": "Test response"
}

Work Item: Build a new user registration feature"""

    try:
        result = await client._call_llm(test_prompt)
        print("SUCCESS!")
        print("Result:", result)
    except Exception as e:
        print("ERROR:", e)

        # Try to check if API key exists
        api_key = os.environ.get("ZAI_API_KEY")
        print(f"API Key exists: {bool(api_key)}")
        if api_key:
            print(f"API Key length: {len(api_key)}")

if __name__ == "__main__":
    asyncio.run(test_api())
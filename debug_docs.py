#!/usr/bin/env python3
"""
Debug script to check document content sizes
"""

from pathlib import Path
from story_size.core.docs import read_documents

def check_document_sizes():
    docs_dir = Path(r"D:\Data\Management\Backlog\Sprint5.8\Konsep Zip Code")

    print(f"Analyzing documents in: {docs_dir}")
    print("Files in directory:")

    for file_path in docs_dir.iterdir():
        if file_path.is_file():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  - {file_path.name}: {size_mb:.2f} MB")

    print("\nReading documents...")
    try:
        content = read_documents(docs_dir)
        content_size = len(content)
        content_mb = content_size / (1024 * 1024)

        print(f"Total content length: {content_size:,} characters")
        print(f"Total content size: {content_mb:.2f} MB")
        print(f"Content preview (first 500 chars):")
        print(content[:500])
        print("...")

        # Check for potential issues
        if content_mb > 1:
            print(f"\n⚠️  WARNING: Content is very large ({content_mb:.2f} MB)")
            print("   This may cause API requests to fail due to token limits")

        if "gist-publish-url" in content:
            print(f"\n📋 Document appears to be from a GitHub gist")
            print("   This is expected behavior for large documents")

    except Exception as e:
        print(f"Error reading documents: {e}")

if __name__ == "__main__":
    check_document_sizes()
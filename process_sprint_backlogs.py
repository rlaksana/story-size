#!/usr/bin/env python3
"""
Script to process all backlog folders in Sprint5.9 directory.
For each folder that contains files, it runs story size estimation and saves output to the folder.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional

def find_backlog_folders(base_path: str) -> List[str]:
    """Find all folders in the Sprint5.9 directory."""
    try:
        base_dir = Path(base_path)
        if not base_dir.exists():
            print(f"Error: Base path {base_path} does not exist")
            return []

        # Get all directories in the base path
        folders = []
        for item in base_dir.iterdir():
            if item.is_dir():
                folders.append(str(item))

        return sorted(folders)
    except Exception as e:
        print(f"Error scanning directories: {e}")
        return []

def has_files(folder_path: str) -> bool:
    """Check if folder contains any files (not just subdirectories)."""
    try:
        folder = Path(folder_path)
        for item in folder.rglob('*'):
            if item.is_file():
                # Skip system files and hidden files
                if not item.name.startswith('.') and item.name != 'Thumbs.db':
                    return True
        return False
    except Exception as e:
        print(f"Error checking files in {folder_path}: {e}")
        return False

def has_story_size_estimation(folder_path: str) -> bool:
    """Check if folder already has story_size_estimation.md file."""
    try:
        estimation_file = Path(folder_path) / "story_size_estimation.md"
        return estimation_file.exists()
    except Exception as e:
        print(f"Error checking story_size_estimation.md in {folder_path}: {e}")
        return False

def run_story_size(docs_dir: str, output_file: str) -> bool:
    """Run story size estimation for a backlog folder."""
    try:
        # Get the path to main.py (assuming script is in the story-size project)
        main_py = Path(__file__).parent / "main.py"

        if not main_py.exists():
            print(f"Error: main.py not found at {main_py}")
            return False

        # Build the command - rely on environment variables for platform paths
        cmd = [
            sys.executable,
            str(main_py),
            "main",
            "--docs-dir", docs_dir,
            "--output-md", output_file
        ]

        # Don't force platforms - let the detector decide based on document content
        # The CLI will automatically pick up platform paths from .env file

        print(f"\nRunning: {' '.join(cmd)}")
        print(f"Processing: {Path(docs_dir).name}")

        # Run the command and wait for completion (no timeout)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Wait for process to complete naturally
        stdout, stderr = process.communicate()
        result = type('Result', (), {
            'returncode': process.returncode,
            'stdout': stdout,
            'stderr': stderr
        })()

        if result.returncode == 0:
            print(f"[OK] Successfully processed: {Path(docs_dir).name}")
            # Print output summary if available
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:  # Show last 5 lines
                    if line.strip():
                        print(f"  {line}")
            # Also print any final score/estimation if found
            if "Final score:" in result.stdout or "Story Points:" in result.stdout:
                for line in result.stdout.split('\n'):
                    if "Final score:" in line or "Story Points:" in line or "Platform:" in line:
                        print(f"  → {line.strip()}")
            return True
        else:
            print(f"[FAIL] Failed to process: {Path(docs_dir).name}")
            if "getaddrinfo failed" in result.stderr or "Max retries exceeded" in result.stderr:
                print("  Network Error: Unable to connect to the API server")
                print("  Please check:")
                print("  - Internet connection")
                print("  - VPN/firewall settings")
                print("  - API endpoint configuration")
            else:
                print(f"Error: {result.stderr[:500]}")  # Limit error output
            return False

    except Exception as e:
        print(f"[ERROR] Error processing {Path(docs_dir).name}: {e}")
        return False

def main():
    """Main function to process all backlog folders."""
    # Base path to Sprint5.9 directory
    base_path = r"D:\Data\Management\Backlog\MVP 6.8 - Andal Payroll"

    print("=" * 60)
    print("Story Size Estimation for All Backlog Folders")
    print("=" * 60)
    print(f"Base directory: {base_path}")
    print("Using platform paths from .env configuration")
    print("=" * 60)

    # Find all backlog folders
    folders = find_backlog_folders(base_path)

    if not folders:
        print("No folders found in the base directory")
        return

    print(f"\nFound {len(folders)} folders to check")

    # Statistics
    processed = 0
    skipped_empty = 0
    skipped_existing = 0
    successful = 0
    failed = 0

    # Process each folder
    for i, folder_path in enumerate(folders, 1):
        folder_name = Path(folder_path).name
        print(f"\n[{i}/{len(folders)}] Checking: {folder_name}")

        # Check if folder already has story size estimation
        if has_story_size_estimation(folder_path):
            print(f"  Skipping (already has estimation): {folder_name}")
            skipped_existing += 1
            continue

        # Check if folder has files
        if not has_files(folder_path):
            print(f"  Skipping (no files): {folder_name}")
            skipped_empty += 1
            continue

        print(f"  Contains files, processing...")

        # Define output file path
        output_file = Path(folder_path) / "story_size_estimation.md"

        # Run story size estimation
        if run_story_size(folder_path, str(output_file)):
            successful += 1
        else:
            failed += 1

        processed += 1

    # Print summary
    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total folders found: {len(folders)}")
    print(f"Empty folders skipped: {skipped_empty}")
    print(f"Already estimated folders skipped: {skipped_existing}")
    print(f"Total folders processed: {processed}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if successful > 0:
        print(f"\n[OK] Story size estimations saved to each respective folder")

    if failed > 0:
        print(f"\n[WARNING] Some folders failed to process. Check the error messages above.")

if __name__ == "__main__":
    main()
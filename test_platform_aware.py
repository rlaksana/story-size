#!/usr/bin/env python3
"""
Test script to demonstrate platform-aware story size estimation functionality
without requiring AI API calls.
"""

import asyncio
from pathlib import Path
from story_size.core.docs import read_documents
from story_size.core.directory_resolver import DirectoryResolver
from story_size.core.code_analysis import analyze_all_platforms
from story_size.core.models import (
    PlatformRequirement, PlatformDetection, PlatformAnalysis, CompleteAnalysis
)
from story_size.config import load_config
from datetime import datetime

async def demo_platform_analysis():
    """Demonstrate the platform-aware analysis pipeline"""

    print("=== Platform-Aware Story Size Estimation Demo ===\n")

    # 1. Load configuration
    print("1. Loading configuration...")
    config = load_config(Path("sample_config.yml"))
    print("   Configuration loaded successfully")

    # 2. Read documents
    print("\n2. Reading work item documents...")
    doc_content = read_documents(Path("test_data/docs"))
    print(f"   Document content: {len(doc_content)} characters")
    print("   Document preview:")
    print(f"   {doc_content[:150]}...")

    # 3. Resolve platform directories
    print("\n3. Resolving platform directories...")
    resolver = DirectoryResolver()
    platform_dirs = resolver.resolve_platform_directories(
        fe_dir=Path("test_data/frontend"),
        be_dir=Path("test_data/backend"),
        mobile_dir=Path("test_data/mobile")
    )

    print("   Platform directories resolved:")
    print(f"   - Frontend: {platform_dirs.fe_dir}")
    print(f"   - Backend: {platform_dirs.be_dir}")
    print(f"   - Mobile: {platform_dirs.mobile_dir}")

    # 4. Analyze platform code
    print("\n4. Analyzing platform code...")
    code_analysis = analyze_all_platforms(platform_dirs)

    print(f"   Total files: {code_analysis.total_files}")
    print(f"   Languages detected: {', '.join(code_analysis.total_languages)}")
    print(f"   Cross-platform dependencies: {len(code_analysis.cross_platform_dependencies)}")

    for platform, summary in code_analysis.platform_summaries.items():
        if summary.files_estimated > 0:
            print(f"   - {platform.upper()}: {summary.files_estimated} files, {len(summary.languages_detected)} languages")
            print(f"     Languages: {', '.join(summary.languages_detected)}")
            print(f"     Key files: {', '.join(summary.key_files[:2])}")

    # 5. Simulate platform detection (normally done by AI)
    print("\n5. Simulating platform detection...")
    platform_requirements = {
        "frontend": PlatformRequirement(required=True, scope="high", technologies=["React", "TypeScript"]),
        "backend": PlatformRequirement(required=True, scope="high", technologies=[".NET", "C#", "SQL Server"]),
        "mobile": PlatformRequirement(required=True, scope="medium", technologies=["React Native"]),
        "devops": PlatformRequirement(required=False, scope="low", technologies=[])
    }

    platform_detection = PlatformDetection(
        platform_requirements=platform_requirements,
        work_item_type="feature",
        complexity_level="complex",
        estimated_platforms=["frontend", "backend", "mobile"],
        confidence=0.85,
        reasoning="Work item requires full-stack development with mobile app"
    )

    print("   Platforms detected:")
    print(f"   - Required platforms: {', '.join(platform_detection.estimated_platforms)}")
    print(f"   - Work item type: {platform_detection.work_item_type}")
    print(f"   - Complexity level: {platform_detection.complexity_level}")
    print(f"   - Confidence: {platform_detection.confidence:.2f}")

    # 6. Simulate platform analyses (normally done by AI)
    print("\n6. Simulating platform-specific analyses...")
    platform_analyses = {}

    for platform in platform_detection.estimated_platforms:
        if platform in code_analysis.platform_summaries:
            summary = code_analysis.platform_summaries[platform]

            # Simulate platform-specific analysis
            platform_analysis = PlatformAnalysis(
                platform=platform,
                factors={
                    "ui_complexity": 4 if platform == "frontend" else 3,
                    "business_logic": 5 if platform == "backend" else 2,
                    "platform_complexity": 3 if platform == "mobile" else 0,
                },
                explanation=f"Complex {platform} development with modern architecture",
                recommended_approach=f"Use best practices for {platform} development",
                estimated_hours={"min": 16, "max": 32},
                key_components=[f"{platform.title()} Dashboard", f"{platform.title()} Authentication"],
                key_challenges=[f"Integration with {platform} systems", "Performance optimization"]
            )

            platform_analyses[platform] = platform_analysis
            print(f"   - {platform.upper()} analysis: {len(platform_analysis.factors)} factors analyzed")

    # 7. Calculate story points
    print("\n7. Calculating story points...")

    # Simple story point calculation for demo
    platform_story_points = {}
    total_score = 0

    for platform, analysis in platform_analyses.items():
        if analysis.factors:
            platform_score = sum(analysis.factors.values())
            platform_sp = 3 if platform_score < 15 else 5 if platform_score < 20 else 8
            platform_story_points[platform] = platform_sp
            total_score += platform_score

    overall_sp = 5 if total_score < 20 else 8 if total_score < 30 else 13

    # 8. Create complete analysis
    complete_analysis = CompleteAnalysis(
        platform_detection=platform_detection,
        platform_analyses=platform_analyses,
        overall_story_points=overall_sp,
        platform_story_points=platform_story_points,
        confidence_score=platform_detection.confidence
    )

    # 9. Display results
    print("\n=== PLATFORM-AWARE ESTIMATION RESULTS ===")
    print(f"Overall Story Points: {complete_analysis.overall_story_points}")
    print(f"Confidence Score: {complete_analysis.confidence_score:.2f}")

    print("\nPlatform Breakdown:")
    for platform, sp in complete_analysis.platform_story_points.items():
        analysis = complete_analysis.platform_analyses[platform]
        hours = f"({analysis.estimated_hours['min']}-{analysis.estimated_hours['max']}h)"
        print(f"  {platform.upper()}: {sp} points {hours}")

    print("\nPlatform Analysis Summary:")
    for platform, analysis in complete_analysis.platform_analyses.items():
        print(f"  {platform.upper()}:")
        print(f"    - Explanation: {analysis.explanation}")
        print(f"    - Approach: {analysis.recommended_approach}")
        print(f"    - Challenges: {', '.join(analysis.key_challenges)}")

    print("\nImplementation Notes:")
    print("  This demo shows the platform-aware architecture without AI calls.")
    print("  In production, the PlatformAwareAIClient would:")
    print("  1. Analyze documents to detect required platforms")
    print("  2. Perform platform-specific complexity analysis")
    print("  3. Generate detailed factor explanations")
    print("  4. Provide implementation recommendations")

if __name__ == "__main__":
    asyncio.run(demo_platform_analysis())
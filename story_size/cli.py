import typer
import asyncio
from pathlib import Path
from typing import List, Optional

from story_size.config import load_config
from story_size.core.docs import read_documents
from story_size.core.code_analysis import analyze_code, analyze_all_platforms
from story_size.core.ai_client import score_factors
from story_size.core.scoring import calculate_complexity_score, map_to_story_points, get_confidence
from story_size.core.models import Estimation, CodeSummary, EnhancedCodeAnalysis
from story_size.core.directory_resolver import DirectoryResolver
from story_size.core.platform_ai_client import PlatformAwareAIClient

app = typer.Typer()

@app.command()
def main(
    # Document Input
    docs_dir: Path = typer.Option(..., "--docs-dir", help="Directory containing the work item's documents."),

    # Platform-Specific Code Directories (NEW)
    fe_dir: Optional[Path] = typer.Option(None, "--fe-dir", help="Frontend code directory (React, Angular, Vue, etc.)."),
    be_dir: Optional[Path] = typer.Option(None, "--be-dir", help="Backend code directory (API, services, business logic)."),
    mobile_dir: Optional[Path] = typer.Option(None, "--mobile-dir", help="Mobile code directory (Flutter, React Native, etc.)."),
    devops_dir: Optional[Path] = typer.Option(None, "--devops-dir", help="DevOps/Infrastructure directory (Docker, K8s, CI/CD)."),

    # Backward compatibility and fallback
    code_dir: Optional[Path] = typer.Option(None, "--code-dir", help="[DEPRECATED] Unified code directory (use platform-specific dirs instead)."),

    # Analysis Options
    auto_detect_dirs: bool = typer.Option(False, "--auto-detect-dirs", help="Auto-detect platform directories from code-dir."),
    force_platforms: Optional[str] = typer.Option(None, "--force-platforms", help="Force analysis for specific platforms: frontend,backend,mobile,devops"),
    use_traditional: bool = typer.Option(False, "--traditional", help="Use traditional analysis instead of platform-aware analysis."),

    # Existing Options
    paths: Optional[str] = typer.Option(None, "--paths", help="Comma-separated subpaths to prioritize within each platform directory."),
    languages: Optional[str] = typer.Option(None, "--languages", help="Comma-separated languages to analyze: csharp,typescript,javascript,dart."),
    output: str = typer.Option("enhanced", "--output", help="Output mode: text, json, enhanced."),
    config: Optional[Path] = typer.Option(None, "--config", help="Configuration file."),
):
    """
    Estimates story points with platform-specific analysis.

    Examples:
    # Platform-specific directories (recommended)
    story-size --docs-dir docs/user-story-123/ --fe-dir frontend/ --be-dir backend/

    # Auto-detect platform directories
    story-size --docs-dir docs/ --code-dir src/ --auto-detect-dirs

    # Force specific platforms
    story-size --docs-dir docs/ --code-dir src/ --force-platforms frontend,backend

    # Use traditional analysis
    story-size --docs-dir docs/ --code-dir src/ --traditional
    """

    # Input validation
    if not docs_dir.is_dir():
        print(f"Error: --docs-dir '{docs_dir}' is not a directory.")
        raise typer.Exit(code=1)

    # Load configuration
    config_data = load_config(config)

    # Parse input options
    parsed_paths = paths.split(',') if paths else None
    parsed_languages = languages.split(',') if languages else None

    # Resolve platform directories
    resolver = DirectoryResolver()
    platform_dirs = resolver.resolve_platform_directories(
        fe_dir=fe_dir,
        be_dir=be_dir,
        mobile_dir=mobile_dir,
        devops_dir=devops_dir,
        code_dir=code_dir,
        auto_detect=auto_detect_dirs
    )

    # Read documents
    doc_text = read_documents(docs_dir)

    if not doc_text.strip():
        print("Warning: No document content found. Analysis may be inaccurate.")

    # Perform analysis
    if use_traditional or not any([fe_dir, be_dir, mobile_dir, devops_dir, auto_detect_dirs]):
        # Traditional analysis (backward compatibility)
        print("Using traditional analysis...")
        estimation = _run_traditional_analysis(doc_text, code_dir, parsed_paths, parsed_languages, config_data, output)
    else:
        # Platform-aware analysis
        print("Using platform-aware analysis...")
        estimation = asyncio.run(_run_platform_analysis(
            doc_text, platform_dirs, parsed_paths, parsed_languages, config_data, output, force_platforms
        ))

    # Output results
    _output_results(estimation, output)

def _run_traditional_analysis(doc_text: str, code_dir: Optional[Path], paths: Optional[List[str]],
                            languages: Optional[List[str]], config_data: dict, output_format: str) -> Estimation:
    """Run traditional analysis for backward compatibility"""

    if not code_dir:
        print("Error: Traditional analysis requires --code-dir")
        raise typer.Exit(code=1)

    code_analysis_summary = analyze_code(code_dir, paths=paths, languages=languages)
    factors, score_explanations = score_factors(doc_text, code_analysis_summary, {}, config_data)

    complexity_score = calculate_complexity_score(factors, config_data.get("weights", {}))
    story_points = map_to_story_points(complexity_score, config_data.get("mapping", {}))
    confidence = get_confidence(factors)

    code_summary = CodeSummary(
        files_estimated=sum(code_analysis_summary["files_by_language"].values()),
        services_touched=[],
        db_migrations_estimated=0,
        languages_seen=code_analysis_summary["languages_seen"]
    )

    return Estimation(
        story_points=story_points,
        scale=[1, 2, 3, 5, 8, 13],
        complexity_score=complexity_score,
        factors=factors,
        confidence=confidence,
        rationale=[],
        code_summary=code_summary,
        score_explanations=score_explanations
    )

async def _run_platform_analysis(doc_text: str, platform_dirs, paths: Optional[List[str]],
                                languages: Optional[List[str]], config_data: dict, output_format: str,
                                force_platforms: Optional[str]):
    """Run platform-aware analysis"""

    # Analyze platform directories
    paths_str = ','.join(paths) if paths else None
    languages_str = ','.join(languages) if languages else None

    code_analysis = analyze_all_platforms(platform_dirs, paths_str, languages_str)

    print(f"\nPlatform Analysis:")
    for platform, summary in code_analysis.platform_summaries.items():
        if summary.files_estimated > 0:
            print(f"  {platform.upper()}: {summary.files_estimated} files, {', '.join(summary.languages_detected)}")

    # Run platform-aware AI analysis
    ai_client = PlatformAwareAIClient(config_data)
    analysis = await ai_client.get_complete_analysis(doc_text, code_analysis)

    return analysis

def _output_results(estimation, output_format: str):
    """Output analysis results in the specified format"""

    if output_format == "json":
        if hasattr(estimation, 'model_dump_json'):
            # Enhanced estimation
            print(estimation.model_dump_json(indent=2))
        else:
            # Traditional estimation
            print(estimation.model_dump_json(indent=2))

    elif output_format == "enhanced" and hasattr(estimation, 'platform_detection'):
        # Enhanced platform-aware output
        _print_enhanced_output(estimation)

    else:
        # Traditional text output
        _print_traditional_output(estimation)

def _print_enhanced_output(analysis):
    """Print enhanced platform-aware output"""

    print(f"\nSTORY SIZE ESTIMATION")
    print(f"Overall: {analysis.overall_story_points} story points (confidence: {analysis.confidence_score:.2f})")

    print(f"\nPLATFORM BREAKDOWN:")
    for platform, sp in analysis.platform_story_points.items():
        platform_analysis = analysis.platform_analyses.get(platform)
        if platform_analysis and platform_analysis.estimated_hours:
            hours = f" ({platform_analysis.estimated_hours['min']}-{platform_analysis.estimated_hours['max']}h)"
        else:
            hours = ""
        print(f"  {platform.upper()}: {sp} points{hours}")

    print(f"\nPLATFORM ANALYSIS:")
    for platform, platform_analysis in analysis.platform_analyses.items():
        if platform_analysis.factors:
            print(f"\n  {platform.upper()}:")
            print(f"    Explanation: {platform_analysis.explanation}")
            print(f"    Approach: {platform_analysis.recommended_approach}")

            if platform_analysis.key_components:
                print(f"    Key Components: {', '.join(platform_analysis.key_components[:3])}")

            if platform_analysis.key_challenges:
                print(f"    Challenges: {', '.join(platform_analysis.key_challenges[:2])}")

    print(f"\nDETECTION DETAILS:")
    print(f"  Work Item Type: {analysis.platform_detection.work_item_type}")
    print(f"  Complexity Level: {analysis.platform_detection.complexity_level}")
    print(f"  Required Platforms: {', '.join(analysis.platform_detection.estimated_platforms)}")
    print(f"  Reasoning: {analysis.platform_detection.reasoning}")

def _print_traditional_output(estimation):
    """Print traditional text output"""

    print(f"Suggested: {estimation.story_points} story points (confidence {estimation.confidence:.2f}), complexity_score={estimation.complexity_score}")
    print(f"Factors: DC={estimation.factors.dc}, IC={estimation.factors.ic}, IB={estimation.factors.ib}, DS={estimation.factors.ds}, NR={estimation.factors.nr}")

    print("\nScore Explanations:")
    print(f"• DC ({estimation.factors.dc}/5): {estimation.score_explanations.dc_explanation}")
    print(f"• IC ({estimation.factors.ic}/5): {estimation.score_explanations.ic_explanation}")
    print(f"• IB ({estimation.factors.ib}/5): {estimation.score_explanations.ib_explanation}")
    print(f"• DS ({estimation.factors.ds}/5): {estimation.score_explanations.ds_explanation}")
    print(f"• NR ({estimation.factors.nr}/5): {estimation.score_explanations.nr_explanation}")

# Add help command
@app.command()
def help_examples():
    """Show usage examples for the story-size tool."""

    examples = """
Story Size Estimator - Usage Examples

PLATFORM-SPECIFIC ANALYSIS (Recommended):
  story-size --docs-dir docs/user-story-123/ --fe-dir frontend/ --be-dir backend/ --mobile-dir mobile/

AUTO-DETECTION:
  story-size --docs-dir docs/ --code-dir src/ --auto-detect-dirs

SPECIFIC PLATFORMS:
  story-size --docs-dir docs/ --code-dir src/ --force-platforms frontend,backend

TRADITIONAL ANALYSIS (Backward Compatible):
  story-size --docs-dir docs/ --code-dir src/ --traditional

OUTPUT FORMATS:
  --output text     (Traditional text output)
  --output json     (JSON format)
  --output enhanced (Platform-aware breakdown)

ADVANCED OPTIONS:
  --paths "api,billing"    (Focus on specific subdirectories)
  --languages "csharp,typescript"  (Specific languages)
  --config custom.yml      (Custom configuration)
    """
    print(examples)

if __name__ == "__main__":
    app()

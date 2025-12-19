import typer
import asyncio
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from story_size.config import load_config
from story_size.core.docs_enhanced import read_documents_with_images
from story_size.core.code_analysis import analyze_all_platforms
from story_size.core.directory_resolver import DirectoryResolver
from story_size.core.platform_ai_client import PlatformAwareAIClient
from story_size.core.models import EnhancedCodeAnalysis

app = typer.Typer()

@app.command()
def main(
    # Document Input
    docs_dir: Optional[Path] = typer.Option(
        None,
        "--docs-dir",
        help="Directory containing the work item's documents.",
        envvar="DEFAULT_BACKLOG_PATH"
    ),

    # Platform-Specific Code Directories (NEW)
    fe_dir: Optional[Path] = typer.Option(None, "--fe-dir", help="Frontend code directory (React, Angular, Vue, etc.).", envvar="DEFAULT_FE_DIR"),
    be_dir: Optional[Path] = typer.Option(None, "--be-dir", help="Backend code directory (API, services, business logic).", envvar="DEFAULT_BE_DIR"),
    mobile_dir: Optional[Path] = typer.Option(None, "--mobile-dir", help="Mobile code directory (Flutter, React Native, etc.).", envvar="DEFAULT_MOBILE_DIR"),
    devops_dir: Optional[Path] = typer.Option(None, "--devops-dir", help="DevOps/Infrastructure directory (Docker, K8s, CI/CD).", envvar="DEFAULT_DEVOPS_DIR"),

  
    # Analysis Options
    auto_detect_dirs: bool = typer.Option(False, "--auto-detect-dirs", help="Auto-detect platform directories from code-dir."),
    force_platforms: Optional[str] = typer.Option(None, "--force-platforms", help="Force analysis for specific platforms: frontend,backend,mobile,devops"),
    code_dir: Optional[Path] = typer.Option(None, "--code-dir", help="Code directory for auto-detection or forced platforms.", envvar="DEFAULT_REPO_PATH"),

    # Existing Options
    paths: Optional[str] = typer.Option(None, "--paths", help="Comma-separated subpaths to prioritize within each platform directory."),
    languages: Optional[str] = typer.Option(None, "--languages", help="Comma-separated languages to analyze: csharp,typescript,javascript,dart."),
    output: str = typer.Option("enhanced", "--output", help="Output mode: json, enhanced."),
    output_md: Optional[Path] = typer.Option(None, "--output-md", help="Save output to markdown file at specified path."),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Default directory for saving markdown reports (used with --output-md).", envvar="DEFAULT_OUTPUT_DIR"),
    save_to_docs: bool = typer.Option(False, "--save-to-docs", help="Save output to markdown file in docs directory with generated filename."),
    auto_save: bool = typer.Option(False, "--auto-save/--no-auto-save", help="Auto-save to output_dir with generated filename.", envvar="DEFAULT_AUTO_SAVE"),
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

    # Save to markdown file
    story-size --docs-dir docs/ --fe-dir frontend/ --be-dir backend/ --output-md reports/estimation.md

    # Auto-save to docs directory
    story-size --docs-dir docs/ --fe-dir frontend/ --be-dir backend/ --save-to-docs

    # Use defaults from .env file
    story-size

    # Mix defaults with overrides
    story-size --fe-dir ../different-frontend --mobile-dir ../different-mobile

    # Save to output directory with custom filename
    story-size --output-md estimation-report.md --output-dir ./reports

    # Auto-save to output directory
    story-size --auto-save
    """

    # Get docs_dir from environment variable if not provided
    if not docs_dir:
        docs_dir_path = os.getenv("DEFAULT_BACKLOG_PATH")
        if not docs_dir_path:
            print("Error: --docs-dir is required (or set DEFAULT_BACKLOG_PATH in .env file).")
            raise typer.Exit(code=1)
        docs_dir = Path(docs_dir_path)

    # Input validation
    if not docs_dir.is_dir():
        print(f"Error: --docs-dir '{docs_dir}' is not a directory.")
        raise typer.Exit(code=1)

    # Load configuration
    config_data = load_config(config)

    # Parse input options
    parsed_paths = paths.split(',') if paths else None
    parsed_languages = languages.split(',') if languages else None

    # Get platform directories from environment variables if not provided
    if not fe_dir and os.getenv("DEFAULT_FE_DIR"):
        fe_dir = Path(os.getenv("DEFAULT_FE_DIR"))
    if not be_dir and os.getenv("DEFAULT_BE_DIR"):
        be_dir = Path(os.getenv("DEFAULT_BE_DIR"))
    if not mobile_dir and os.getenv("DEFAULT_MOBILE_DIR"):
        mobile_dir = Path(os.getenv("DEFAULT_MOBILE_DIR"))
    if not devops_dir and os.getenv("DEFAULT_DEVOPS_DIR"):
        devops_dir = Path(os.getenv("DEFAULT_DEVOPS_DIR"))

    # Get output_dir from environment variable if not provided
    if not output_dir and os.getenv("DEFAULT_OUTPUT_DIR"):
        output_dir = Path(os.getenv("DEFAULT_OUTPUT_DIR"))

    # Handle DEFAULT_AUTO_SAVE environment variable (convert string to bool)
    if os.getenv("DEFAULT_AUTO_SAVE"):
        env_auto_save = os.getenv("DEFAULT_AUTO_SAVE").lower()
        if env_auto_save in ('true', '1', 'yes', 'on'):
            auto_save = True
        elif env_auto_save in ('false', '0', 'no', 'off'):
            auto_save = False

  
    # Get code_dir from environment variable if not provided
    if not code_dir:
        code_dir_path = os.getenv("DEFAULT_REPO_PATH")
        if code_dir_path:
            code_dir = Path(code_dir_path)

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

    # Read documents with image processing and OCR support
    # Enhanced processing includes image extraction, OCR, and visual complexity analysis
    # Use adaptive content length based on image processing needs
    doc_result = read_documents_with_images(docs_dir, max_content_length=500000)
    doc_text = doc_result['text_content']

    # Smart content trimming for large documents with images
    # Reduce text length when we have substantial OCR data to prevent API timeouts
    total_images = doc_result.get('total_images', 0)
    total_ocr_chars = doc_result.get('total_ocr_chars', 0)

    if total_images > 0:
        # Calculate reduction factor based on image content
        # More images + more OCR text = more aggressive trimming
        image_factor = min(total_images * 0.1, 0.6)  # Up to 60% reduction for many images (increased from 50%)
        ocr_factor = min(total_ocr_chars / 10000, 0.4)  # Up to 40% reduction for OCR text (increased from 30%)
        total_reduction = image_factor + ocr_factor

        # Cap total reduction to 70% to ensure we still have meaningful content
        total_reduction = min(total_reduction, 0.7)

        # Apply reduction to text content
        max_length = int(30000 * (1 - total_reduction))
        if len(doc_text) > max_length:
            doc_text = doc_text[:max_length]
            print(f"  [INFO] Trimmed document content to {max_length} characters (reduced by {int(total_reduction*100)}%) due to {total_images} images and {total_ocr_chars} OCR characters")

    if not doc_text.strip():
        print("Warning: No document content found. Analysis may be inaccurate.")

    # Platform-aware analysis
    print("Using platform-aware analysis...")
    estimation = asyncio.run(_run_platform_analysis(
        doc_text, platform_dirs, parsed_paths, parsed_languages, config_data, output, force_platforms, doc_result
    ))

    # Handle auto-save to docs directory
    if save_to_docs and not output_md:
        from datetime import datetime
        docs_dir_name = docs_dir.name.replace(" ", "_").replace("(", "").replace(")", "").replace("[", "").replace("]", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_md = docs_dir / f"story-estimation_{docs_dir_name}_{timestamp}.md"
    elif auto_save and not output_md and output_dir:
        # Auto-save to output_dir with generated filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        docs_dir_name = docs_dir.name.replace(" ", "_").replace("(", "").replace(")", "").replace("[", "").replace("]", "")
        output_md = output_dir / f"story-estimation_{docs_dir_name}_{timestamp}.md"
    elif output_dir and output_md and not output_md.parent.exists() and str(output_md.parent) == ".":
        # If output_md is just a filename (no directory), prepend output_dir
        output_md = output_dir / output_md

    # Output results
    _output_results(estimation, output, output_md)


async def _run_platform_analysis(doc_text: str, platform_dirs, paths: Optional[List[str]],
                                languages: Optional[List[str]], config_data: dict, output_format: str,
                                force_platforms: Optional[str], image_analysis: dict = None):
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
    analysis = await ai_client.get_complete_analysis(doc_text, code_analysis, force_platforms, image_analysis)

    return analysis

def _output_results(estimation, output_format: str, output_md: Optional[Path] = None):
    """Output analysis results in the specified format"""

    # Generate console output
    if output_format == "json":
        console_output = estimation.model_dump_json(indent=2)
        print(console_output)
    else:
        # Enhanced platform-aware output (default)
        console_output = _get_enhanced_output_text(estimation)
        print(console_output)

    # Save to markdown file if requested
    if output_md:
        _save_to_markdown(estimation, output_md, output_format, console_output)

def _get_enhanced_output_text(analysis) -> str:
    """Get enhanced platform-aware output as text"""

    lines = []
    lines.append("STORY SIZE ESTIMATION")
    lines.append(f"Overall: {analysis.overall_story_points} story points (confidence: {analysis.confidence_score:.2f})")

    lines.append("")
    lines.append("PLATFORM BREAKDOWN:")
    for platform, sp in analysis.platform_story_points.items():
        platform_analysis = analysis.platform_analyses.get(platform)
        if platform_analysis and platform_analysis.estimated_hours:
            hours = f" ({platform_analysis.estimated_hours['min']}-{platform_analysis.estimated_hours['max']}h)"
        else:
            hours = ""
        lines.append(f"  {platform.upper()}: {sp} points{hours}")

    lines.append("")
    lines.append("PLATFORM ANALYSIS:")
    for platform, platform_analysis in analysis.platform_analyses.items():
        if platform_analysis.factors:
            lines.append("")
            lines.append(f"  {platform.upper()}:")
            lines.append(f"    Explanation: {platform_analysis.explanation}")
            lines.append(f"    Approach: {platform_analysis.recommended_approach}")
            
            # Display individual factors (DC, IC, IB, DS, NR)
            lines.append("    Factors:")
            for factor_name, factor_value in platform_analysis.factors.items():
                lines.append(f"      {factor_name}: {factor_value}")

            if platform_analysis.key_components:
                lines.append(f"    Key Components: {', '.join(platform_analysis.key_components[:3])}")

            if platform_analysis.key_challenges:
                lines.append(f"    Challenges: {', '.join(platform_analysis.key_challenges[:2])}")

    lines.append("")
    lines.append("DETECTION DETAILS:")
    lines.append(f"  Work Item Type: {analysis.platform_detection.work_item_type}")
    lines.append(f"  Complexity Level: {analysis.platform_detection.complexity_level}")
    lines.append(f"  Required Platforms: {', '.join(analysis.platform_detection.estimated_platforms)}")
    lines.append(f"  Reasoning: {analysis.platform_detection.reasoning}")

    return "\n".join(lines)


def _save_to_markdown(estimation, output_path: Path, output_format: str, console_output: str):
    """Save analysis results to a markdown file"""

    from datetime import datetime

    try:
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate markdown content
        lines = []

        # Header
        lines.append("# Story Size Estimation Report")
        lines.append("")
        lines.append(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Output Format:** {output_format}")
        lines.append("")

        # Summary table - Platform-aware analysis
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| **Overall Story Points** | {estimation.overall_story_points} |")
        lines.append(f"| **Confidence Score** | {estimation.confidence_score:.2f} |")
        lines.append(f"| **Work Item Type** | {estimation.platform_detection.work_item_type} |")
        lines.append(f"| **Complexity Level** | {estimation.platform_detection.complexity_level} |")
        lines.append(f"| **Required Platforms** | {', '.join(estimation.platform_detection.estimated_platforms)} |")
        lines.append("")

        # Platform breakdown table
        lines.append("## Platform Breakdown")
        lines.append("")
        lines.append("| Platform | Story Points | Estimated Hours |")
        lines.append("|----------|-------------|-----------------|")

        for platform, sp in estimation.platform_story_points.items():
            platform_analysis = estimation.platform_analyses.get(platform)
            if platform_analysis and platform_analysis.estimated_hours:
                hours = f"{platform_analysis.estimated_hours['min']}-{platform_analysis.estimated_hours['max']}"
            else:
                hours = "N/A"
            lines.append(f"| {platform.upper()} | {sp} | {hours} |")
        lines.append("")

        # Platform analysis with factors
        lines.append("## Platform Analysis with Factors")
        lines.append("")
        
        for platform, platform_analysis in estimation.platform_analyses.items():
            lines.append(f"### {platform.upper()}")
            lines.append("")
            
            if platform_analysis.factors:
                lines.append("**Factors:**")
                lines.append("")
                lines.append("| Factor | Score |")
                lines.append("|--------|-------|")
                for factor_name, factor_value in platform_analysis.factors.items():
                    lines.append(f"| {factor_name} | {factor_value} |")
                lines.append("")
            
            lines.append(f"**Explanation:** {platform_analysis.explanation}")
            lines.append("")
            lines.append(f"**Recommended Approach:** {platform_analysis.recommended_approach}")
            lines.append("")
            
            if platform_analysis.key_components:
                lines.append(f"**Key Components:** {', '.join(platform_analysis.key_components)}")
                lines.append("")
            
            if platform_analysis.key_challenges:
                lines.append(f"**Key Challenges:** {', '.join(platform_analysis.key_challenges)}")
                lines.append("")
            
            if platform_analysis.estimated_hours:
                lines.append(f"**Estimated Hours:** {platform_analysis.estimated_hours['min']}-{platform_analysis.estimated_hours['max']} hours")
                lines.append("")
            
            lines.append("---")
            lines.append("")

        # Detailed analysis
        lines.append("## Detailed Analysis")
        lines.append("")
        lines.append("```")
        lines.append(console_output)
        lines.append("```")
        lines.append("")

        # Metadata
        lines.append("## Analysis Metadata")
        lines.append("")
        lines.append(f"- **Reasoning:** {estimation.platform_detection.reasoning}")
        lines.append("")
        lines.append("### Platform Requirements:")
        for platform, req in estimation.platform_detection.platform_requirements.items():
            if req.required:
                lines.append(f"  - **{platform.upper()}:** Required (Scope: {req.scope})")
                if req.technologies:
                    lines.append(f"    - Technologies: {', '.join(req.technologies)}")
            else:
                lines.append(f"  - **{platform.upper()}:** Not Required")

        lines.append("")
        lines.append("---")
        lines.append("*Report generated by Story Size Estimator*")

        # Write to file
        markdown_content = "\n".join(lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        print(f"\nReport saved to: {output_path}")

    except Exception as e:
        print(f"Error saving markdown file: {e}")

# Add correction command
@app.command()
def correct(
    docs_dir: Path = typer.Argument(..., help="Directory containing the work item's documents."),
    detected_platforms: str = typer.Option(..., "--detected", help="Platforms detected by AI (comma-separated)."),
    correct_platforms: str = typer.Option(..., "--correct", help="Actual correct platforms (comma-separated)."),
    app_name: Optional[str] = typer.Option(None, "--app", help="Application name if known."),
    feedback: Optional[str] = typer.Option(None, "--feedback", help="Optional feedback about why AI was wrong.")
):
    """Record a correction to improve AI learning."""

    from story_size.core.platform_detector import PlatformDetector
    from story_size.core.docs_enhanced import read_documents_with_images

    # Load document text
    try:
        doc_result = read_documents_with_images(docs_dir)
        doc_text = doc_result['text_content']
    except Exception as e:
        print(f"Error reading documents: {e}")
        return

    # Parse platforms
    detected = [p.strip() for p in detected_platforms.split(',')]
    correct = [p.strip() for p in correct_platforms.split(',')]

    # Record correction
    detector = PlatformDetector()
    detector.learning_system.record_correction(
        doc_text=doc_text,
        detected_platforms=detected,
        correct_platforms=correct,
        application_name=app_name,
        user_feedback=feedback
    )

    print(f"[SUCCESS] Correction recorded successfully!")
    print(f"  Document: {docs_dir}")
    print(f"  Detected: {', '.join(detected)}")
    print(f"  Correct: {', '.join(correct)}")
    if app_name:
        print(f"  Application: {app_name}")

    # Show learning statistics
    stats = detector.learning_system.get_statistics()
    print(f"\nLearning Statistics:")
    print(f"  Total corrections: {stats['total_corrections']}")
    print(f"  Applications learned: {stats['applications_learned']}")
    print(f"  Patterns learned: {stats['patterns_learned']}")

    if stats['top_corrected_apps']:
        print("\nTop corrected applications:")
        for app in stats['top_corrected_apps'][:3]:
            print(f"  • {app['name']}: {app['corrections']} corrections (confidence: {app['confidence']:.2f})")

# Add help command
@app.command()
def help_examples():
    """Show usage examples for the story-size tool."""

    examples = """
Story Size Estimator - Usage Examples

ENVIRONMENT VARIABLES (.env file):
  DEFAULT_BACKLOG_PATH=../taiga-gitea-integration/backlog
  DEFAULT_REPO_PATH=../taiga-web
  DEFAULT_FE_DIR=../taiga-web/frontend
  DEFAULT_BE_DIR=../taiga-web/backend
  DEFAULT_MOBILE_DIR=../taiga-web/mobile
  DEFAULT_DEVOPS_DIR=../taiga-web/devops
  DEFAULT_OUTPUT_DIR=./reports
  DEFAULT_AUTO_SAVE=true

PLATFORM-SPECIFIC ANALYSIS (Recommended):
  story-size --docs-dir docs/user-story-123/ --fe-dir frontend/ --be-dir backend/ --mobile-dir mobile/

USE ENVIRONMENT VARIABLES:
  story-size

MIX DEFAULTS WITH OVERRIDES:
  story-size --fe-dir ../different-frontend --mobile-dir ../different-mobile

MACHINE LEARNING FEATURES:

1. AUTOMATIC PLATFORM DETECTION:
   The tool learns from your applications over time and improves accuracy.
   - Recognizes "Andal Connect" as mobile app
   - Recognizes "Andal Kharisma" as web application
   - Learns from corrections to avoid future mistakes

2. RECORD CORRECTIONS (when AI gets it wrong):
   story-size correct docs/backlog-123/ \\
     --detected frontend,backend \\
     --correct mobile,backend \\
     --app "Andal Connect" \\
     --feedback "This is a mobile app, not web"

3. CHECK LEARNING STATISTICS:
   After recording corrections, the tool shows:
   - Total corrections recorded
   - Applications it has learned
   - Confidence scores for each learned application

SAVE REPORTS:
  story-size --output-md estimation-report.md                    # Save to current directory
  story-size --output-md estimation.md --output-dir ./reports    # Save to specific directory
  story-size --auto-save                                          # Auto-save to DEFAULT_OUTPUT_DIR
  story-size --no-auto-save                                        # Disable auto-save (when DEFAULT_AUTO_SAVE=true)

AUTO-DETECTION:
  story-size --docs-dir docs/ --code-dir src/ --auto-detect-dirs

SPECIFIC PLATFORMS:
  story-size --docs-dir docs/ --code-dir src/ --force-platforms frontend,backend

OUTPUT FORMATS:
  --output json     (JSON format)
  --output enhanced (Platform-aware breakdown - default)

ADVANCED OPTIONS:
  --paths "api,billing"    (Focus on specific subdirectories)
  --languages "csharp,typescript"  (Specific languages)
  --config custom.yml      (Custom configuration)
    """
    print(examples)

if __name__ == "__main__":
    app()

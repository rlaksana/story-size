from pathlib import Path
from typing import Dict, List, Optional
from story_size.core.models import PlatformCodeSummary, EnhancedCodeAnalysis, PlatformDirectories
from story_size.core.directory_resolver import DirectoryResolver


def generate_project_tree(platform_dir: Path, until_depth: int = 3) -> str:
    """
    Generate hierarchical tree view of platform directory.

    Args:
        platform_dir: Root directory to generate tree from
        until_depth: Maximum depth to traverse (default: 3 levels)

    Returns:
        String representation of directory tree with ASCII art connectors
    """
    if not platform_dir or not platform_dir.exists():
        return f"{platform_dir.name if platform_dir else '(empty)'} (directory not found)"

    tree_lines = []
    root_name = platform_dir.name
    tree_lines.append(root_name + "/")

    # Skip common directories to ignore
    skip_dirs = {'.git', '.idea', '.vscode', 'node_modules', '__pycache__',
                 '.dart_tool', 'build', 'dist', 'bin', 'obj', '.venv', 'venv',
                 'target', '.next', '.nuxt', 'vendor', 'coverage'}

    # Skip common file patterns
    skip_files = {'.gitignore', '.ds_store', 'thumbs.db', 'desktop.ini',
                  'package-lock.json', 'yarn.lock', 'pubspec.lock', '.gitkeep'}

    def add_tree(path: Path, prefix: str = "", depth: int = 0):
        if depth > until_depth:
            return

        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            # Filter out skipped items
            items = [item for item in items
                     if item.name.lower() not in skip_dirs
                     and item.name.lower() not in skip_files
                     and not item.name.startswith('.')]

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                item_suffix = "/" if item.is_dir() else ""
                tree_lines.append(f"{prefix}{connector}{item.name}{item_suffix}")

                if item.is_dir():
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    add_tree(item, next_prefix, depth + 1)
        except (PermissionError, OSError):
            pass

    add_tree(platform_dir)
    return "\n".join(tree_lines)


SUPPORTED_LANGUAGES = {
    "csharp": [".cs"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx"],
    "dart": [".dart"],
    "python": [".py"],
    "java": [".java"],
    "go": [".go"],
    "yaml": [".yml", ".yaml"],
    "json": [".json"],
    "dockerfile": ["dockerfile", "Dockerfile"],
}


# Enhanced platform-specific functions
def analyze_platform_code(
    platform: str,
    platform_dir: Optional[Path],
    paths: Optional[List[str]] = None,
    languages: Optional[List[str]] = None
) -> PlatformCodeSummary:
    """Analyze code for a specific platform"""

    if not platform_dir or not platform_dir.exists():
        return PlatformCodeSummary(
            platform=platform,
            directory=None,
            files_estimated=0,
            languages_detected=[],
            key_files=[],
            loc_by_language={},
            complexity_indicators={},
            project_tree=None
        )

    # Get platform-specific language priorities, but filter to supported languages
    resolver = DirectoryResolver()
    all_platform_languages = resolver.get_platform_languages(platform, languages)
    platform_languages = [lang for lang in all_platform_languages if lang in SUPPORTED_LANGUAGES]

    # If no languages specified or supported, use default supported languages
    if not platform_languages:
        platform_languages = list(SUPPORTED_LANGUAGES.keys())

    # Analyze the platform directory
    files_by_language = {lang: 0 for lang in platform_languages}
    loc_by_language = {lang: 0 for lang in platform_languages}
    large_files_by_language = {lang: 0 for lang in platform_languages}

    search_paths = [platform_dir]
    if paths:
        search_paths = [platform_dir / p for p in paths]

    for search_path in search_paths:
        for lang in platform_languages:
            extensions = SUPPORTED_LANGUAGES[lang]
            for ext in extensions:
                for file_path in search_path.rglob(f"*{ext}"):
                    files_by_language[lang] += 1
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            loc = len(lines)
                            loc_by_language[lang] += loc
                            if loc > 500:
                                large_files_by_language[lang] += 1
                    except Exception:
                        # Ignore files that can't be read
                        pass

    analysis = {
        "languages_seen": [lang for lang, count in files_by_language.items() if count > 0],
        "files_by_language": files_by_language,
        "loc_by_language": loc_by_language,
        "large_files_by_language": large_files_by_language,
    }

    # Identify platform-specific key files
    key_files = resolver.identify_key_files(platform_dir, platform)

    # Calculate platform complexity indicators
    complexity_indicators = calculate_platform_complexity(analysis, platform)

    # Generate project tree for AI context (depth 7 for enterprise projects)
    project_tree = generate_project_tree(platform_dir, until_depth=7)

    return PlatformCodeSummary(
        platform=platform,
        directory=platform_dir,
        files_estimated=sum(analysis["files_by_language"].values()),
        languages_detected=analysis["languages_seen"],
        key_files=key_files,
        loc_by_language=analysis["loc_by_language"],
        complexity_indicators=complexity_indicators,
        project_tree=project_tree
    )

def get_platform_primary_languages(platform: str, user_languages: Optional[List[str]]) -> List[str]:
    """Get priority languages for a platform"""

    platform_defaults = {
        "frontend": ["typescript", "javascript"],
        "backend": ["csharp", "python", "java", "go"],
        "mobile": ["dart", "kotlin", "swift"],
        "devops": ["yaml", "json"]
    }

    if user_languages:
        # Filter user languages by platform relevance
        platform_langs = platform_defaults.get(platform, [])
        return [lang for lang in user_languages if lang in platform_langs] or platform_langs

    return platform_defaults.get(platform, [])

def calculate_platform_complexity(analysis: Dict, platform: str) -> Dict[str, any]:
    """Calculate platform-specific complexity indicators"""

    complexity_indicators = {
        "large_files": analysis.get("large_files_by_language", {}),
        "total_loc": sum(analysis.get("loc_by_language", {}).values()),
        "file_count": sum(analysis.get("files_by_language", {}).values()),
        "language_diversity": len(analysis.get("languages_seen", []))
    }

    # Add platform-specific indicators
    if platform == "frontend":
        complexity_indicators["has_typescript"] = "typescript" in analysis.get("languages_seen", [])
        complexity_indicators["has_multiple_frameworks"] = len(analysis.get("languages_seen", [])) > 1

    elif platform == "backend":
        complexity_indicators["has_database_files"] = any(ext in [".sql", ".db", ".sqlite"]
                                                       for ext in [] for _ in range(1))
        complexity_indicators["has_config_files"] = any(ext in [".json", ".yml", ".yaml", ".xml"]
                                                     for ext in [] for _ in range(1))

    elif platform == "mobile":
        complexity_indicators["is_flutter"] = "dart" in analysis.get("languages_seen", [])
        complexity_indicators["is_native"] = any(lang in analysis.get("languages_seen", [])
                                               for lang in ["kotlin", "swift", "java"])

    elif platform == "devops":
        complexity_indicators["has_containerization"] = any(file in ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]
                                                          for file in [])
        complexity_indicators["has_kubernetes"] = any(file in [] for file in [])
        complexity_indicators["has_ci_cd"] = any(path in analysis for path in [".github", "ci-cd", "pipeline"])

    return complexity_indicators

def analyze_all_platforms(
    platform_dirs: PlatformDirectories,
    paths: Optional[str] = None,
    languages: Optional[str] = None
) -> EnhancedCodeAnalysis:
    """Analyze all provided platform directories"""

    parsed_paths = paths.split(',') if paths else None
    parsed_languages = languages.split(',') if languages else None

    platform_summaries = {}

    platforms = ["frontend", "backend", "mobile", "devops"]
    platform_field_mapping = {
        "frontend": "fe_dir",
        "backend": "be_dir",
        "mobile": "mobile_dir",
        "devops": "devops_dir"
    }

    # Check if any platform directories are provided
    platform_dirs_provided = any(getattr(platform_dirs, field) for field in platform_field_mapping.values())

    if platform_dirs_provided:
        # Analyze provided platform directories
        for platform in platforms:
            platform_dir = getattr(platform_dirs, platform_field_mapping[platform])

            if platform_dir:
                summary = analyze_platform_code(
                    platform=platform,
                    platform_dir=platform_dir,
                    paths=parsed_paths,
                    languages=parsed_languages
                )
                platform_summaries[platform] = summary
    else:
        # Fallback to unified directory analysis
        if platform_dirs.unified_dir:
            unified_summary = analyze_code(
                code_dir=platform_dirs.unified_dir,
                paths=parsed_paths,
                languages=parsed_languages
            )
            # Convert to platform summaries based on language detection
            platform_summaries = convert_unified_to_platform_summaries(unified_summary, platform_dirs.unified_dir)

    return EnhancedCodeAnalysis(
        platform_summaries=platform_summaries,
        total_files=sum(summary.files_estimated for summary in platform_summaries.values()),
        total_languages=list(set(lang for summary in platform_summaries.values() for lang in summary.languages_detected)),
        cross_platform_dependencies=identify_cross_platform_dependencies(platform_summaries)
    )

def convert_unified_to_platform_summaries(unified_analysis: Dict, base_dir: Path) -> Dict[str, PlatformCodeSummary]:
    """Convert unified code analysis to platform-specific summaries"""

    platform_summaries = {}

    # Language to platform mapping
    language_platforms = {
        "typescript": "frontend",
        "javascript": "frontend",
        "csharp": "backend",
        "python": "backend",
        "java": "backend",
        "go": "backend",
        "dart": "mobile",
        "kotlin": "mobile",
        "swift": "mobile",
        "yaml": "devops",
        "json": "devops"
    }

    # Group files by platform
    platform_files = {platform: [] for platform in ["frontend", "backend", "mobile", "devops"]}

    for lang, count in unified_analysis["files_by_language"].items():
        if count > 0 and lang in language_platforms:
            platform = language_platforms[lang]
            platform_files[platform].append(lang)

    # Create platform summaries
    for platform, languages_detected in platform_files.items():
        if languages_detected:
            # Filter analysis data for this platform
            platform_analysis = {
                key: {lang: value for lang, value in val.items() if lang in languages_detected}
                for key, val in unified_analysis.items()
                if isinstance(val, dict)
            }

            resolver = DirectoryResolver()
            platform_summaries[platform] = PlatformCodeSummary(
                platform=platform,
                directory=base_dir,
                files_estimated=sum(platform_analysis.get("files_by_language", {}).values()),
                languages_detected=languages_detected,
                key_files=resolver.identify_key_files(base_dir, platform),
                loc_by_language=platform_analysis.get("loc_by_language", {}),
                complexity_indicators=calculate_platform_complexity(platform_analysis, platform)
            )

    return platform_summaries

def identify_cross_platform_dependencies(platform_summaries: Dict[str, PlatformCodeSummary]) -> List[str]:
    """Identify potential cross-platform dependencies"""

    dependencies = []

    # Check for common integration patterns
    frontend_summary = platform_summaries.get("frontend")
    backend_summary = platform_summaries.get("backend")

    if frontend_summary and backend_summary:
        if frontend_summary.files_estimated > 0 and backend_summary.files_estimated > 0:
            dependencies.append("Frontend-Backend API Integration")

    # Check for mobile+backend
    mobile_summary = platform_summaries.get("mobile")
    if mobile_summary and backend_summary:
        if mobile_summary.files_estimated > 0 and backend_summary.files_estimated > 0:
            dependencies.append("Mobile-Backend API Integration")

    # Check for DevOps involvement
    devops_summary = platform_summaries.get("devops")
    if devops_summary and devops_summary.files_estimated > 0:
        total_other_files = sum(summary.files_estimated for platform, summary in platform_summaries.items()
                               if platform != "devops")
        if total_other_files > 0:
            dependencies.append("DevOps Deployment & Infrastructure")

    return dependencies


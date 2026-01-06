"""
Impact Analyzer - Automatically detects which files are affected by a work item

Combines:
1. AI-based entity extraction from requirements
2. Codebase search for matching files
3. Dependency analysis for cascading changes

Eliminates the need for manual --paths flag.
"""

from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import re
from datetime import datetime

from story_size.core.models import PlatformCodeSummary, EnhancedCodeAnalysis


@dataclass
class EntityMatch:
    """Represents a matched entity in a file"""
    entity: str
    file_path: Path
    match_count: int
    match_type: str  # filename, content, import, class, function


@dataclass
class ImpactScope:
    """Represents the analyzed impact scope"""
    requirement: str
    extracted_entities: List[str]
    directly_affected_files: List[Path]
    cascading_affected_files: List[Path]
    total_affected_files: int
    total_files_in_platform: int
    impact_ratio: float  # 0.0 to 1.0
    confidence: float


class EntityExtractor:
    """Extract entities/features from requirement text using patterns + AI"""

    # Pattern-based entity extraction (fast, heuristic)
    ENTITY_PATTERNS = [
        # Noun phrases that might be entities
        r"(?:add|update|delete|modify|create|implement|refactor)\s+([A-Z][a-zA-Z]+)",
        r"(?:for|to|in|with|on)\s+(?:the\s+)?([A-Z][a-zA-Z]+)",
        r"([A-Z][a-zA-Z]+)\s+(?:page|screen|form|component|service|controller|module)",
        r"([A-Z][a-zA-Z]+)\s+(?:authentication|authorization|login|logout|registration)",
    ]

    # Common technical terms to exclude
    EXCLUDE_TERMS = {
        "API", "JWT", "JSON", "SQL", "UI", "UX", "HTTP", "HTTPS",
        "GDP", "GDPR", "SSL", "TLS", "REST", "SOAP", "GraphQL",
        "The", "This", "That", "It", "User", "All", "Some", "Any",
        "First", "Last", "Next", "Previous", "New", "Old",
        "Please", "Note", "See", "Also", "And", "Or", "But", "For",
        "With", "From", "Into", "Onto", "Upon", "Within", "Without",
        "System", "Application", "Platform", "Feature", "Function",
        "Code", "File", "Test", "Build", "Deploy", "Release",
        "Issue", "Bug", "Fix", "Error", "Exception", "Problem",
    }

    # Technology-specific entity patterns
    CODE_PATTERNS = {
        "csharp": [
            r"(?:class|interface|struct)\s+([A-Z][a-zA-Z0-9_]+)",
            r"(?:public|private|protected|internal)\s+(?:static\s+)?(?:class|interface)\s+([A-Z][a-zA-Z0-9_]+)",
            r"([A-Z][a-zA-Z0-9_]+)\s*(?:Controller|Service|Repository|Model|ViewModel|Dto)",
        ],
        "typescript": [
            r"(?:class|interface|type)\s+([A-Z][a-zA-Z0-9_]+)",
            r"(?:export\s+)?(?:const|function|class)\s+([A-Z][a-zA-Z0-9_]+)",
            r"([A-Z][a-zA-Z0-9_]+)\s*(?:Component|Service|Directive|Pipe|Module)",
        ],
        "javascript": [
            r"(?:class|function|const)\s+([A-Z][a-zA-Z0-9_]+)",
            r"module\.exports\s*=\s*([A-Z][a-zA-Z0-9_]+)",
        ],
        "dart": [
            r"(?:class|enum|mixin)\s+([A-Z][a-zA-Z0-9_]+)",
            r"([A-Z][a-zA-Z0-9_]+)\s*(?:Widget|Page|Screen|Controller|Service|Model)",
        ],
        "python": [
            r"(?:class|def)\s+([A-Z][a-zA-Z0-9_]+)",
        ],
        "java": [
            r"(?:class|interface|enum)\s+([A-Z][a-zA-Z0-9_]+)",
            r"([A-Z][a-zA-Z0-9_]+)\s*(?:Controller|Service|Repository|Entity|Dto)",
        ],
    }

    def extract_from_requirement(self, requirement: str) -> List[str]:
        """
        Extract potential entities from requirement text.

        Uses pattern matching for speed, falls back to AI if needed.
        """
        entities = set()

        # Pattern-based extraction
        for pattern in self.ENTITY_PATTERNS:
            matches = re.findall(pattern, requirement, re.IGNORECASE)
            for match in matches:
                entity = match.strip() if isinstance(match, str) else match
                if len(entity) >= 3 and entity not in self.EXCLUDE_TERMS:
                    entities.add(entity.capitalize())

        # Extract capitalized words (potential proper nouns/entities)
        capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', requirement)
        for word in capitalized_words:
            if len(word) >= 3 and word not in self.EXCLUDE_TERMS:
                entities.add(word)

        return list(entities)

    def extract_from_code(self, file_path: Path, language: str) -> List[str]:
        """Extract class/function names from source code"""
        entities = []

        if not file_path.exists():
            return entities

        patterns = self.CODE_PATTERNS.get(language, [])

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            for pattern in patterns:
                matches = re.findall(pattern, content)
                entities.extend(matches)

        except (OSError, IOError, UnicodeDecodeError):
            pass

        return list(set(entities))


class CodebaseSearcher:
    """Search codebase for files related to extracted entities"""

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir

    def search_entities(self, entities: List[str], platform_summary: PlatformCodeSummary) -> List[EntityMatch]:
        """
        Search for entities in the codebase.

        Returns list of files that match the entities.
        """
        matches = []

        if not self.code_dir or not self.code_dir.exists():
            return matches

        # Search in filenames first (fastest)
        for entity in entities:
            entity_variants = self._get_entity_variants(entity)

            for file_path in self.code_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                # Filename match
                if self._matches_filename(file_path, entity_variants)):
                    matches.append(EntityMatch(
                        entity=entity,
                        file_path=file_path,
                        match_count=1,
                        match_type="filename"
                    ))
                    continue

                # Content match (for source files only)
                if file_path.suffix.lower() in {'.cs', '.ts', '.tsx', '.js', '.jsx', '.py', '.dart', '.go', '.java'}:
                    content_matches = self._search_file_content(file_path, entity_variants)
                    if content_matches > 0:
                        matches.append(EntityMatch(
                            entity=entity,
                            file_path=file_path,
                            match_count=content_matches,
                            match_type="content"
                        ))

        return matches

    def _get_entity_variants(self, entity: str) -> List[str]:
        """Get different naming variations of an entity"""
        variants = [entity]

        # Common naming patterns
        variants.extend([
            entity.lower(),
            entity.upper(),
            entity + "Controller",
            entity + "Service",
            entity + "Repository",
            entity + "Model",
            entity + "Dto",
            entity + "ViewModel",
            entity + "Component",
            entity + "Page",
            entity + "Screen",
            entity + "Widget",
            entity + "Helper",
            entity + "Utility",
            # Snake case variants
            re.sub(r'(?<!^)(?=[A-Z])', '_', entity).lower(),
            # Kebab case variants
            re.sub(r'(?<!^)(?=[A-Z])', '-', entity).lower(),
        ])

        return variants

    def _matches_filename(self, file_path: Path, entity_variants: List[str]) -> bool:
        """Check if filename matches any entity variant"""
        filename = file_path.stem.lower()

        for variant in entity_variants:
            if variant.lower() in filename:
                return True

        return False

    def _search_file_content(self, file_path: Path, entity_variants: List[str]) -> int:
        """Search for entity references in file content"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            match_count = 0

            for variant in entity_variants:
                # Count word-boundary matches
                pattern = r'\b' + re.escape(variant) + r'\b'
                matches = re.findall(pattern, content, re.IGNORECASE)
                match_count += len(matches)

            return match_count

        except (OSError, IOError, UnicodeDecodeError):
            return 0


class DependencyAnalyzer:
    """Analyze dependencies to find cascading changes"""

    # Import patterns for different languages
    IMPORT_PATTERNS = {
        "csharp": [
            r"using\s+([\w.]+);",
            r"namespace\s+([\w.]+)",
        ],
        "typescript": [
            r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
            r"import\s+\{[^}]+\}\s+from\s+['\"]([^'\"]+)['\"]",
        ],
        "javascript": [
            r"require\(['\"]([^'\"]+)['\"]\)",
            r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
        ],
        "dart": [
            r"import\s+['\"]([^'\"]+)['\"]",
        ],
        "python": [
            r"from\s+([\w.]+)\s+import",
            r"import\s+([\w.]+)",
        ],
    }

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir

    def find_cascading_changes(self, directly_affected: List[Path],
                              platform_summary: PlatformCodeSummary) -> List[Path]:
        """
        Find files that depend on the directly affected files.

        If A changes, any file that imports A is also affected.
        """
        cascading = set()

        if not self.code_dir or not self.code_dir.exists():
            return list(cascading)

        # Build import graph
        import_graph = self._build_import_graph(platform_summary)

        # For each directly affected file, find its dependents
        for affected_file in directly_affected:
            file_key = str(affected_file.relative_to(self.code_dir))

            # Find files that import this file
            for file_path, imports in import_graph.items():
                if file_key in imports or any(file_key in imp for imp in imports):
                    dependent_path = self.code_dir / file_path
                    if dependent_path not in directly_affected:
                        cascading.add(dependent_path)

        # Also check test files (tests for affected code)
        for affected_file in directly_affected:
            test_files = self._find_test_files(affected_file)
            cascading.update(test_files)

        return list(cascading)

    def _build_import_graph(self, platform_summary: PlatformCodeSummary) -> Dict[str, Set[str]]:
        """Build a graph of file imports"""
        graph = {}

        for language in platform_summary.languages_detected:
            pattern_key = language.lower()
            if pattern_key not in self.IMPORT_PATTERNS:
                continue

            patterns = self.IMPORT_PATTERNS[pattern_key]

            # Get file extension for language
            extension_map = {
                "csharp": ".cs",
                "typescript": [".ts", ".tsx"],
                "javascript": [".js", ".jsx"],
                "dart": ".dart",
                "python": ".py",
            }

            extensions = extension_map.get(pattern_key, [])
            if isinstance(extensions, str):
                extensions = [extensions]

            for ext in extensions:
                for file_path in self.code_dir.rglob(f"*{ext}"):
                    imports = self._extract_imports(file_path, patterns)
                    if imports:
                        graph[str(file_path.relative_to(self.code_dir))] = imports

        return graph

    def _extract_imports(self, file_path: Path, patterns: List[str]) -> Set[str]:
        """Extract imports from a file"""
        imports = set()

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            for pattern in patterns:
                matches = re.findall(pattern, content)
                imports.update(matches)

        except (OSError, IOError, UnicodeDecodeError):
            pass

        return imports

    def _find_test_files(self, source_file: Path) -> List[Path]:
        """Find test files related to a source file"""
        test_files = []

        # Common test patterns
        test_patterns = [
            source_file.name.replace(".cs", ".Tests.cs"),
            source_file.name.replace(".ts", ".test.ts"),
            source_file.name.replace(".ts", ".spec.ts"),
            source_file.name.replace(".dart", "_test.dart"),
            source_file.name.replace(".py", "_test.py"),
            source_file.name.replace(".py", "test_" + source_file.name),
        ]

        # Look in test directories
        test_dirs = ["tests", "test", "__tests__", "spec", "specs"]

        for test_dir in test_dirs:
            test_dir_path = self.code_dir / test_dir
            if test_dir_path.exists():
                for pattern in test_patterns:
                    matches = list(test_dir_path.rglob(pattern))
                    test_files.extend(matches)

        return test_files


class ImpactAnalyzer:
    """Main impact analysis orchestrator"""

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir
        self.entity_extractor = EntityExtractor()
        self.codebase_searcher = CodebaseSearcher(code_dir)
        self.dependency_analyzer = DependencyAnalyzer(code_dir)

    def analyze_impact(self, requirement: str, platform_summary: PlatformCodeSummary) -> ImpactScope:
        """
        Analyze the impact scope of a work item on a platform.

        Args:
            requirement: The work item requirement text
            platform_summary: Code analysis for the platform

        Returns:
            ImpactScope with affected files and impact ratio
        """
        # Step 1: Extract entities from requirement
        entities = self.entity_extractor.extract_from_requirement(requirement)

        # If no entities found, try AI extraction (placeholder for future LLM integration)
        if not entities:
            # TODO: Use LLM to extract entities
            # entities = self._extract_entities_with_llm(requirement)
            pass

        # Step 2: Search for files containing those entities
        entity_matches = self.codebase_searcher.search_entities(entities, platform_summary)

        # Deduplicate files
        directly_affected = list(set(match.file_path for match in entity_matches))

        # If no direct matches, use a broader search
        if not directly_affected:
            directly_affected = self._fallback_broad_search(requirement, platform_summary)

        # Step 3: Find cascading changes (dependencies)
        cascading_affected = self.dependency_analyzer.find_cascading_changes(
            directly_affected, platform_summary
        )

        # Step 4: Calculate impact metrics
        all_affected = list(set(directly_affected + cascading_affected))
        total_files = platform_summary.files_estimated

        impact_ratio = len(all_affected) / total_files if total_files > 0 else 0.0

        # Confidence based on match quality
        confidence = self._calculate_confidence(entity_matches, len(all_affected), total_files)

        return ImpactScope(
            requirement=requirement,
            extracted_entities=entities,
            directly_affected_files=directly_affected,
            cascading_affected_files=cascading_affected,
            total_affected_files=len(all_affected),
            total_files_in_platform=total_files,
            impact_ratio=impact_ratio,
            confidence=confidence
        )

    def _fallback_broad_search(self, requirement: str, platform_summary: PlatformCodeSummary) -> List[Path]:
        """
        Fallback: Look for files based on keywords from requirement
        """
        keywords = self._extract_keywords(requirement)
        matches = []

        for keyword in keywords:
            for file_path in self.code_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                # Check filename
                if keyword.lower() in file_path.name.lower():
                    matches.append(file_path)

                # Check content for source files
                elif file_path.suffix.lower() in {'.cs', '.ts', '.tsx', '.js', '.dart', '.py'}:
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        if keyword.lower() in content.lower():
                            matches.append(file_path)
                            break  # One match per keyword is enough
                    except (OSError, IOError, UnicodeDecodeError):
                        pass

        return list(set(matches))

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Remove common words
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                    "with", "by", "from", "as", "is", "was", "are", "were", "been", "be"}

        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) >= 4]

        # Return top 10 most frequent
        from collections import Counter
        word_counts = Counter(keywords)
        return [w for w, _ in word_counts.most_common(10)]

    def _calculate_confidence(self, entity_matches: List[EntityMatch],
                             affected_count: int, total_files: int) -> float:
        """
        Calculate confidence in the impact analysis.

        Higher confidence when:
        - More entity matches found
        - Higher match counts per file
        - Reasonable impact ratio (not 0%, not 100%)
        """
        if not entity_matches:
            return 0.3  # Low confidence for no matches

        base_confidence = 0.5

        # More matches = higher confidence
        match_boost = min(len(entity_matches) * 0.05, 0.3)

        # Impact ratio within reasonable range
        impact_ratio = affected_count / total_files if total_files > 0 else 0
        if 0.01 <= impact_ratio <= 0.5:
            ratio_boost = 0.2
        elif 0.5 < impact_ratio <= 0.8:
            ratio_boost = 0.1
        else:
            ratio_boost = 0.0

        confidence = base_confidence + match_boost + ratio_boost
        return min(confidence, 1.0)


def analyze_all_platforms_impact(requirement: str,
                                 code_analysis: EnhancedCodeAnalysis) -> Dict[str, ImpactScope]:
    """
    Analyze impact across all platforms.

    Returns impact scope for each platform.
    """
    results = {}

    for platform, summary in code_analysis.platform_summaries.items():
        if summary.files_estimated == 0:
            continue

        code_dir = summary.directory
        if not code_dir or not code_dir.exists():
            continue

        analyzer = ImpactAnalyzer(code_dir)
        impact = analyzer.analyze_impact(requirement, summary)
        results[platform] = impact

    return results

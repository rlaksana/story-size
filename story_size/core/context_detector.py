"""
Automatic Context Detection from Codebase

Auto-detects the three critical enhancement factors from Gemini discussion:
1. Legacy Status - from file ages, code patterns, dependencies
2. Traffic Volume - from infrastructure configs, scaling, caching
3. Risk Keywords - from requirements, comments, code patterns
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re
from dataclasses import dataclass

from story_size.core.enhanced_schema import LegacyStatus, TrafficVolume, ProjectContext, TechStackContext


@dataclass
class LegacyIndicators:
    """Indicators that contribute to legacy status assessment"""
    old_file_ratio: float = 0.0           # Ratio of files > 2 years old
    tech_debt_comments: int = 0           # TODO/FIXME/HACK comments
    deprecated_usage: int = 0             # Deprecated APIs/annotations
    old_dependencies: int = 0             # Dependencies > 3 years old
    spaghetti_indicators: int = 0         # Large files, deep nesting
    total_score: int = 0                  # Combined legacy score (0-100)


@dataclass
class TrafficIndicators:
    """Indicators that contribute to traffic volume assessment"""
    has_load_balancer: bool = False       # nginx, traefik, alb, etc.
    has_caching: bool = False             # redis, memcached, cdn
    has_auto_scaling: bool = False        # k8s hpa, aws autoscaling
    has_rate_limiting: bool = False       # rate limit middleware
    has_monitoring: bool = False          # prometheus, datadog, etc.
    has_cluster_setup: bool = False       # kubernetes, swarm
    total_score: int = 0                  # Combined traffic score (0-100)


class LegacyStatusDetector:
    """Detect legacy status from codebase patterns"""

    # Patterns indicating technical debt
    TECH_DEBT_PATTERNS = [
        r"TODO", r"FIXME", r"HACK", r"XXX",
        r"REFACTOR", r"DEPRECATED", r"LEGACY",
        r"tech.*debt", r"technical.*debt"
    ]

    # Deprecated API patterns across languages
    DEPRECATED_PATTERNS = [
        r"@deprecated", r"\[Obsolete\]", r"# Deprecated",
        r"deprecated:", r"--deprecated", r"legacy:"
    ]

    # Spaghetti code indicators
    SPAGHETTI_PATTERNS = [
        r"if.*if.*if",                     # Deep nesting
        r"catch.*Exception.*\{.*\}",       # Generic catch-all
    ]

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir

    def detect(self) -> LegacyStatus:
        """Detect legacy status from codebase"""
        if not self.code_dir or not self.code_dir.exists():
            return LegacyStatus.GREENFIELD

        indicators = self._collect_indicators()

        # Map score to legacy status
        if indicators.total_score >= 70:
            return LegacyStatus.CRITICAL
        elif indicators.total_score >= 50:
            return LegacyStatus.HIGH
        elif indicators.total_score >= 30:
            return LegacyStatus.MODERATE
        elif indicators.total_score >= 15:
            return LegacyStatus.LOW
        else:
            return LegacyStatus.GREENFIELD

    def _collect_indicators(self) -> LegacyIndicators:
        """Collect all legacy indicators from codebase"""
        indicators = LegacyIndicators()

        # File age analysis (last modified time)
        two_years_ago = datetime.now() - timedelta(days=730)
        file_ages = []

        # Tech debt comments
        tech_debt_count = 0

        # Deprecated API usage
        deprecated_count = 0

        # Spaghetti code indicators
        spaghetti_count = 0

        for file_path in self.code_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip binary and large files
            if file_path.suffix.lower() in ['.exe', '.dll', '.so', '.dylib', '.bin']:
                continue

            # Check file age
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                file_ages.append(mtime)
            except (OSError, IOError):
                pass

            # Scan source files for patterns
            if file_path.suffix.lower() in {'.cs', '.ts', '.tsx', '.js', '.jsx', '.py', '.dart', '.go', '.java'}:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')

                    # Count tech debt comments
                    for pattern in self.TECH_DEBT_PATTERNS:
                        tech_debt_count += len(re.findall(pattern, content, re.IGNORECASE))

                    # Count deprecated usage
                    for pattern in self.DEPRECATED_PATTERNS:
                        deprecated_count += len(re.findall(pattern, content, re.IGNORECASE))

                    # Count spaghetti indicators
                    for pattern in self.SPAGHETTI_PATTERNS:
                        spaghetti_count += len(re.findall(pattern, content, re.IGNORECASE))

                except (OSError, IOError, UnicodeDecodeError):
                    pass

        # Calculate old file ratio
        if file_ages:
            old_files = sum(1 for age in file_ages if age < two_years_ago)
            indicators.old_file_ratio = old_files / len(file_ages)

        indicators.tech_debt_comments = tech_debt_count
        indicators.deprecated_usage = deprecated_count
        indicators.spaghetti_indicators = spaghetti_count

        # Calculate total score (0-100)
        indicators.total_score = self._calculate_legacy_score(indicators)

        return indicators

    def _calculate_legacy_score(self, indicators: LegacyIndicators) -> int:
        """Calculate legacy score from indicators (0-100)"""
        score = 0

        # Old file ratio: 0-25 points
        score += int(indicators.old_file_ratio * 25)

        # Tech debt comments: 0-25 points (capped at 50 comments)
        score += min(indicators.tech_debt_comments, 50) * 0.5

        # Deprecated usage: 0-20 points (capped at 20)
        score += min(indicators.deprecated_usage, 20)

        # Spaghetti indicators: 0-30 points (capped at 30)
        score += min(indicators.spaghetti_indicators, 30)

        return min(int(score), 100)


class TrafficVolumeDetector:
    """Detect traffic volume from infrastructure configuration"""

    # Load balancer configurations
    LOAD_BALANCER_PATTERNS = [
        r"nginx\.conf", r"traefik", r"haproxy",
        r"aws.*alb", r"aws.*elb", r"aws.*nlb",
        r"load.?balancer", r"lb\.conf"
    ]

    # Caching configurations
    CACHING_PATTERNS = [
        r"redis", r"memcached", r"memcache",
        r"varnish", r"squid", r"cdn",
        r"cache", r"@Cacheable"
    ]

    # Auto-scaling configurations
    AUTOSCALING_PATTERNS = [
        r"HorizontalPodAutoscaler", r"hp[a-z]*\.yaml",
        r"aws.*autoscaling", r"scaling.?policy",
        r"autoscaling", r"auto.?scale"
    ]

    # Rate limiting patterns
    RATE_LIMIT_PATTERNS = [
        r"rate.?limit", r"throttle", r"quota",
        r"@RateLimit", r"RateLimiter"
    ]

    # Monitoring/Observability
    MONITORING_PATTERNS = [
        r"prometheus", r"grafana", r"datadog",
        r"newrelic", r"appdynamics", r"splunk",
        r"opentelemetry", r"jaeger", r"zipkin"
    ]

    # Container orchestration
    CLUSTER_PATTERNS = [
        r"kubernetes", r"k8s", r"openshift",
        r"docker.*swarm", r"eks", r"gke", r"aks"
    ]

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir

    def detect(self) -> TrafficVolume:
        """Detect traffic volume from infrastructure"""
        if not self.code_dir or not self.code_dir.exists():
            return TrafficVolume.NONE

        indicators = self._collect_indicators()

        # Map score to traffic volume
        if indicators.total_score >= 70:
            return TrafficVolume.CRITICAL
        elif indicators.total_score >= 50:
            return TrafficVolume.HIGH
        elif indicators.total_score >= 30:
            return TrafficVolume.MEDIUM
        elif indicators.total_score >= 15:
            return TrafficVolume.LOW
        else:
            return TrafficVolume.NONE

    def _collect_indicators(self) -> TrafficIndicators:
        """Collect all traffic indicators from codebase"""
        indicators = TrafficIndicators()

        # Scan for configuration files and infrastructure code
        for file_path in self.code_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Check filename for patterns
            filename = file_path.name.lower()

            # Check load balancer configs
            if any(re.search(pattern, filename, re.IGNORECASE) for pattern in self.LOAD_BALANCER_PATTERNS):
                indicators.has_load_balancer = True

            # Check caching configs
            if any(re.search(pattern, filename, re.IGNORECASE) for pattern in self.CACHING_PATTERNS):
                indicators.has_caching = True

            # Check auto-scaling configs
            if any(re.search(pattern, filename, re.IGNORECASE) for pattern in self.AUTOSCALING_PATTERNS):
                indicators.has_auto_scaling = True

            # Also scan file content for patterns
            if file_path.suffix.lower() in {'.yml', '.yaml', '.json', '.conf', '.cs', '.ts', '.py', '.go'}:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    content_lower = content.lower()

                    # Check rate limiting
                    if not indicators.has_rate_limiting:
                        if any(re.search(pattern, content_lower, re.IGNORECASE) for pattern in self.RATE_LIMIT_PATTERNS):
                            indicators.has_rate_limiting = True

                    # Check monitoring
                    if not indicators.has_monitoring:
                        if any(re.search(pattern, content_lower, re.IGNORECASE) for pattern in self.MONITORING_PATTERNS):
                            indicators.has_monitoring = True

                    # Check cluster setup
                    if not indicators.has_cluster_setup:
                        if any(re.search(pattern, content_lower, re.IGNORECASE) for pattern in self.CLUSTER_PATTERNS):
                            indicators.has_cluster_setup = True

                except (OSError, IOError, UnicodeDecodeError):
                    pass

        # Calculate total score (0-100)
        indicators.total_score = self._calculate_traffic_score(indicators)

        return indicators

    def _calculate_traffic_score(self, indicators: TrafficIndicators) -> int:
        """Calculate traffic score from indicators (0-100)"""
        score = 0

        if indicators.has_load_balancer:
            score += 20
        if indicators.has_caching:
            score += 15
        if indicators.has_auto_scaling:
            score += 25
        if indicators.has_rate_limiting:
            score += 15
        if indicators.has_monitoring:
            score += 15
        if indicators.has_cluster_setup:
            score += 10

        return score


class RiskKeywordDetector:
    """Detect risk keywords from requirements and code comments"""

    # Risk keyword categories
    RISK_KEYWORDS = {
        "legacy": ["legacy", "migration", "migrate", "refactor", "rewrite"],
        "performance": ["performance", "scalability", "optimize", "slow", "latency", "throughput"],
        "security": ["security", "authentication", "authorization", "encryption", "vulnerability", "compliance"],
        "integration": ["integration", "api", "third-party", "external", "webhook", "callback"],
        "data_migration": ["data migration", "schema change", "database", "migration", "rollback"],
        "uncertainty": ["tbd", "to be defined", "pending", "clarify", "discuss", "investigate"]
    }

    def detect_from_text(self, text: str) -> Dict[str, List[str]]:
        """Detect risk keywords from requirements text"""
        detected = {category: [] for category in self.RISK_KEYWORDS}

        text_lower = text.lower()

        for category, keywords in self.RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected[category].append(keyword)

        return detected

    def calculate_risk_multiplier(self, detected_keywords: Dict[str, List[str]]) -> Tuple[float, str]:
        """
        Calculate risk multiplier based on detected keywords.

        Returns:
            (multiplier, rationale)
        """
        total_keywords = sum(len(keywords) for keywords in detected_keywords.values())
        categories_with_risks = sum(1 for keywords in detected_keywords.values() if keywords)

        # Base multiplier: 1.0
        multiplier = 1.0

        # Add 0.05 for each keyword (max 0.30 from keywords)
        multiplier += min(total_keywords * 0.05, 0.30)

        # Add 0.05 for each risk category (max 0.20 from categories)
        multiplier += min(categories_with_risks * 0.05, 0.20)

        # Specific high-risk category adjustments
        if detected_keywords.get("uncertainty"):
            multiplier += 0.10  # Uncertainty warrants buffer

        if detected_keywords.get("data_migration"):
            multiplier += 0.15  # Data migrations are high-risk

        if detected_keywords.get("security"):
            multiplier += 0.10  # Security requires extra care

        # Cap at 2.0
        multiplier = min(multiplier, 2.0)

        # Generate rationale
        rationale_parts = []
        if total_keywords == 0:
            rationale = "No significant risk factors detected."
        else:
            for category, keywords in detected_keywords.items():
                if keywords:
                    rationale_parts.append(f"{category.replace('_', ' ').title()}: {', '.join(keywords)}")

            rationale = f"Risk factors detected: {len(rationale_parts)} categories ({total_keywords} keywords). " + "; ".join(rationale_parts)

        return round(multiplier, 2), rationale


class TechStackDetector:
    """Auto-detect tech stack from codebase"""

    FRAMEWORK_PATTERNS = {
        # Frontend
        "react": [r"package\.json", r"react", r"next\.config", r"use.*react"],
        "vue": [r"vue\.config", r"package\.json", r"vue", r"vuetify"],
        "angular": [r"angular\.json", r"package\.json", r"@angular/"],
        "svelte": [r"svelte\.config", r"package\.json", r"svelte"],

        # Backend
        "asp.net": [r"\.csproj", r"startup\.cs", r"program\.cs", r"webapi"],
        "express": [r"package\.json", r"express"],
        "fastapi": [r"requirements\.txt", r"pyproject\.toml", r"fastapi"],
        "django": [r"requirements\.txt", r"settings\.py", r"django"],
        "spring": [r"pom\.xml", r"build\.gradle", r"spring"],
        "gin": [r"go\.mod", r"gin"],

        # Mobile
        "flutter": [r"pubspec\.yaml", r"lib/main\.dart", r"flutter"],
        "react-native": [r"package\.json", r"react-native"],

        # Database
        "sql-server": [r"appsettings.*json", r"sqlserver", r"mssql"],
        "postgresql": [r"requirements\.txt", r"psycopg", r"postgresql"],
        "mongodb": [r"requirements\.txt", r"pymongo", r"mongodb"],
        "redis": [r"requirements\.txt", r"redis", r"stackexchange\.redis"],

        # Infrastructure
        "docker": [r"dockerfile", r"docker-compose"],
        "kubernetes": [r"deployment\.yaml", r"service\.yaml", r"k8s"],
        "terraform": [r"\.tf", r"terraform"],
        "aws": [r"aws", r"cloudformation", r"cdk"],
    }

    def __init__(self, code_dir: Path):
        self.code_dir = code_dir

    def detect(self) -> TechStackContext:
        """Detect tech stack from codebase"""
        if not self.code_dir or not self.code_dir.exists():
            return TechStackContext()

        frontend = []
        backend = []
        database = []
        infrastructure = []
        third_party = []

        # Scan package/dependency files
        for file_path in self.code_dir.rglob("*"):
            if not file_path.is_file():
                continue

            filename = file_path.name.lower()
            ext = file_path.suffix.lower()

            # Key files to scan
            if filename in {"package.json", "requirements.txt", "pubspec.yaml", "pom.xml",
                           "build.gradle", "go.mod", "csproj", ".csproj"} or \
               ext in {".yml", ".yaml", ".json", ".cs", ".py", ".go", ".dart"}:

                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore').lower()
                except (OSError, IOError, UnicodeDecodeError):
                    continue

                # Detect frameworks
                for framework, patterns in self.FRAMEWORK_PATTERNS.items():
                    if any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns):
                        if framework in {"react", "vue", "angular", "svelte"}:
                            if framework not in frontend:
                                frontend.append(framework)
                        elif framework in {"asp.net", "express", "fastapi", "django", "spring", "gin"}:
                            if framework not in backend:
                                backend.append(framework)
                        elif framework in {"flutter", "react-native"}:
                            if framework not in backend:  # Mobile as backend for now
                                backend.append(framework)
                        elif framework in {"sql-server", "postgresql", "mongodb", "redis"}:
                            if framework not in database:
                                database.append(framework)
                        elif framework in {"docker", "kubernetes", "terraform", "aws"}:
                            if framework not in infrastructure:
                                infrastructure.append(framework)

        return TechStackContext(
            frontend_stack=frontend,
            backend_stack=backend,
            database_stack=database,
            infrastructure=infrastructure,
            third_party_integrations=third_party
        )


def auto_detect_context(code_dir: Path, requirements_text: str = "") -> dict:
    """
    Auto-detect all context from codebase.

    Args:
        code_dir: Path to code directory
        requirements_text: User story/requirement text for keyword detection

    Returns:
        Dictionary containing:
            - legacy_status: LegacyStatus enum
            - traffic_volume: TrafficVolume enum
            - tech_stack: TechStackContext object
            - risk_keywords: Dict of detected keywords by category
            - risk_multiplier: Calculated risk multiplier
            - risk_rationale: Explanation of risk assessment
    """
    if not code_dir or not code_dir.exists():
        return {
            "legacy_status": LegacyStatus.GREENFIELD,
            "traffic_volume": TrafficVolume.NONE,
            "tech_stack": TechStackContext(),
            "risk_keywords": {},
            "risk_multiplier": 1.0,
            "risk_rationale": "No codebase provided for analysis."
        }

    # Detect legacy status
    legacy_detector = LegacyStatusDetector(code_dir)
    legacy_status = legacy_detector.detect()

    # Detect traffic volume
    traffic_detector = TrafficVolumeDetector(code_dir)
    traffic_volume = traffic_detector.detect()

    # Detect tech stack
    tech_detector = TechStackDetector(code_dir)
    tech_stack = tech_detector.detect()

    # Detect risk keywords from requirements
    risk_detector = RiskKeywordDetector()
    risk_keywords = risk_detector.detect_from_text(requirements_text)
    risk_multiplier, risk_rationale = risk_detector.calculate_risk_multiplier(risk_keywords)

    return {
        "legacy_status": legacy_status,
        "traffic_volume": traffic_volume,
        "tech_stack": tech_stack,
        "risk_keywords": risk_keywords,
        "risk_multiplier": risk_multiplier,
        "risk_rationale": risk_rationale
    }

"""
Enhanced Schema for Context-Aware Story Point Estimation

This schema incorporates the three critical enhancements from the Gemini discussion:
1. Context (Tech Stack, Legacy Status, Traffic Volume)
2. Uncertainty (Risk Multiplier)
3. Integration Overhead (Platform aggregation with context switching)
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum

# ============================================================================
# INPUT SCHEMA - Context-First Approach
# ============================================================================

class LegacyStatus(str, Enum):
    """Legacy codebase impact levels"""
    GREENFIELD = "greenfield"          # New code, no constraints
    LOW = "low_legacy"                 # Minor legacy integration
    MODERATE = "moderate_legacy"       # Significant legacy constraints
    HIGH = "high_legacy"               # Heavy legacy, major constraints
    CRITICAL = "critical_legacy"       # Full legacy replacement

class TrafficVolume(str, Enum):
    """Traffic volume impact on deployment risk"""
    NONE = "no_traffic"                # Internal/admin tools
    LOW = "low_traffic"                # < 100 users
    MEDIUM = "medium_traffic"          # 100-1000 users
    HIGH = "high_traffic"              # 1000-10000 users
    CRITICAL = "critical_traffic"      # 10000+ users, high availability

class TechStackContext(BaseModel):
    """Technical context that influences complexity"""
    frontend_stack: List[str] = Field(default_factory=list, description="Frontend frameworks/libraries")
    backend_stack: List[str] = Field(default_factory=list, description="Backend frameworks/languages")
    database_stack: List[str] = Field(default_factory=list, description="Databases used")
    infrastructure: List[str] = Field(default_factory=list, description="Cloud providers, containers, etc.")
    third_party_integrations: List[str] = Field(default_factory=list, description="External APIs/services")

class ProjectContext(BaseModel):
    """Environmental context that affects complexity"""
    legacy_status: LegacyStatus = Field(default=LegacyStatus.GREENFIELD, description="Legacy codebase impact")
    traffic_volume: TrafficVolume = Field(default=TrafficVolume.NONE, description="Production traffic impact")
    team_experience: Literal["junior", "mixed", "senior"] = Field(default="mixed", description="Team experience level")
    timeline_pressure: Literal["relaxed", "normal", "urgent"] = Field(default="normal", description="Timeline constraints")
    quality_requirements: List[str] = Field(default_factory=list, description="Compliance, security, performance requirements")

class WorkItemInput(BaseModel):
    """Complete input for enhanced story point estimation"""
    # Core requirement
    title: str
    description: str
    acceptance_criteria: List[str] = Field(default_factory=list)

    # Contextual information (NEW from Gemini discussion)
    tech_stack: TechStackContext = Field(default_factory=TechStackContext)
    project_context: ProjectContext = Field(default_factory=ProjectContext)

    # Existing documentation/code
    docs_dir: Optional[str] = None
    code_dir: Optional[str] = None

    # Scope filtering
    paths: List[str] = Field(default_factory=list, description="Specific paths to prioritize")
    languages: List[str] = Field(default_factory=list, description="Languages to focus on")

# ============================================================================
# INTERMEDIATE SCHEMA - Risk Detection
# ============================================================================

class RiskDetection(BaseModel):
    """AI-detected risk factors that trigger multipliers"""
    detected_keywords: List[str] = Field(description="Keywords that triggered risk detection")
    risk_category: Literal["low", "medium", "high", "critical"] = Field(description="Overall risk category")

    # Specific risk factors
    has_legacy_risk: bool = Field(default=False, description="Legacy system interaction")
    has_performance_risk: bool = Field(default=False, description="Performance/scalability concerns")
    has_security_risk: bool = Field(default=False, description="Security/compliance requirements")
    has_integration_risk: bool = Field(default=False, description="Third-party/external dependencies")
    has_data_migration_risk: bool = Field(default=False, description="Data schema changes")
    has_uncertainty_risk: bool = Field(default=False, description="Vague or incomplete requirements")

    risk_multiplier: float = Field(ge=1.0, le=2.0, description="Multiplier applied to final score (1.0-2.0)")
    rationale: str = Field(description="Explanation of why this multiplier was chosen")

# ============================================================================
# PLATFORM SCORING - Context-Aware
# ============================================================================

class PlatformScore(BaseModel):
    """Platform-specific score with context awareness"""
    platform: Literal["frontend", "backend", "mobile", "devops"]
    base_score: float = Field(ge=0.0, le=25.0, description="Raw complexity score before multiplier")

    # Five factors (1-5 scale each)
    factor_scores: Dict[str, int] = Field(description="Individual factor scores (1-5)")
    factor_explanations: Dict[str, str] = Field(description="Explanation for each factor score")

    # Context-aware adjustments
    context_adjustment: float = Field(default=0.0, description="Score adjustment based on context")
    context_rationale: str = Field(default="", description="Why context affected this score")

    @property
    def adjusted_score(self) -> float:
        """Score after context adjustment"""
        return self.base_score + self.context_adjustment

# ============================================================================
# AGGREGATION - Integration Overhead
# ============================================================================

class IntegrationOverhead(BaseModel):
    """Calculates the 'glue cost' of combining platforms"""
    platform_count: int = Field(description="Number of platforms involved")
    complexity_level: Literal["low", "medium", "high"] = Field(description="Integration complexity")

    # Context switching cost
    context_switching_multiplier: float = Field(ge=1.0, le=1.5, description="Multiplier for working across platforms")
    integration_complexity_multiplier: float = Field(ge=1.0, le=1.3, description="Multiplier for integration difficulty")

    @property
    def total_integration_multiplier(self) -> float:
        """Combined integration overhead multiplier"""
        return self.context_switching_multiplier * self.integration_complexity_multiplier

# ============================================================================
# OUTPUT SCHEMA - Enhanced Estimation
# ============================================================================

class EnhancedEstimationResult(BaseModel):
    """Complete enhanced estimation result"""

    # Input (echoed back)
    input: WorkItemInput

    # Risk detection
    risk_detection: RiskDetection

    # Platform scores
    platform_scores: List[PlatformScore] = Field(description="Per-platform scores with context")

    # Integration overhead
    integration_overhead: IntegrationOverhead

    # Final calculation
    raw_platform_sum: float = Field(description="Sum of all platform adjusted scores")
    integration_adjusted_score: float = Field(description="Score after integration overhead applied")
    final_score: float = Field(description="Score after risk multiplier applied")

    # Fibonacci mapping
    story_points: int = Field(description="Final story points (Fibonacci scale)")
    fibonacci_mapping: Dict[str, int] = Field(description="The ranges used for mapping")

    # Confidence and rationale
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in estimation")
    rationale: List[str] = Field(description="Step-by-step explanation of the calculation")

    # Hours estimation (with uncertainty ranges)
    estimated_hours: Dict[str, float] = Field(description="Min, most_likely, max hours")
    uncertainty_ratio: float = Field(description="Max/Min ratio (higher = more uncertainty)")

# ============================================================================
# AGGREGATION FORMULA (from Gemini discussion)
# ============================================================================

def calculate_enhanced_story_points(
    platform_scores: List[PlatformScore],
    integration_overhead: IntegrationOverhead,
    risk_multiplier: float
) -> EnhancedEstimationResult:
    """
    Enhanced aggregation formula from Gemini discussion:

    1. Sum platform scores (with context adjustments)
    2. Apply integration overhead (context switching + glue cost)
    3. Apply risk multiplier (uncertainty buffer)
    4. Map to nearest Fibonacci number

    Formula:
        final_score = (sum(platform_scores) * integration_multiplier) * risk_multiplier
        story_points = nearest_fibonacci(final_score)
    """

    # Step 1: Sum platform scores
    raw_sum = sum(p.adjusted_score for p in platform_scores)

    # Step 2: Apply integration overhead
    integration_adjusted = raw_sum * integration_overhead.total_integration_multiplier

    # Step 3: Apply risk multiplier
    final_score = integration_adjusted * risk_multiplier

    # Step 4: Map to Fibonacci
    fibonacci_sequence = [1, 2, 3, 5, 8, 13, 21]
    story_points = min(fibonacci_sequence, key=lambda x: abs(x - final_score))

    return EnhancedEstimationResult(
        platform_scores=platform_scores,
        integration_overhead=integration_overhead,
        raw_platform_sum=raw_sum,
        integration_adjusted_score=integration_adjusted,
        final_score=final_score,
        story_points=story_points
    )

# ============================================================================
# JSON SCHEMA EXPORT (for API documentation)
# ============================================================================

ENHANCED_INPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Enhanced Story Point Estimation Input",
    "type": "object",
    "required": ["title", "description"],
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
        "tech_stack": {
            "type": "object",
            "properties": {
                "frontend_stack": {"type": "array", "items": {"type": "string"}},
                "backend_stack": {"type": "array", "items": {"type": "string"}},
                "database_stack": {"type": "array", "items": {"type": "string"}},
                "infrastructure": {"type": "array", "items": {"type": "string"}},
                "third_party_integrations": {"type": "array", "items": {"type": "string"}}
            }
        },
        "project_context": {
            "type": "object",
            "properties": {
                "legacy_status": {
                    "type": "string",
                    "enum": ["greenfield", "low_legacy", "moderate_legacy", "high_legacy", "critical_legacy"]
                },
                "traffic_volume": {
                    "type": "string",
                    "enum": ["no_traffic", "low_traffic", "medium_traffic", "high_traffic", "critical_traffic"]
                },
                "team_experience": {"type": "string", "enum": ["junior", "mixed", "senior"]},
                "timeline_pressure": {"type": "string", "enum": ["relaxed", "normal", "urgent"]},
                "quality_requirements": {"type": "array", "items": {"type": "string"}}
            }
        },
        "docs_dir": {"type": "string"},
        "code_dir": {"type": "string"},
        "paths": {"type": "array", "items": {"type": "string"}},
        "languages": {"type": "array", "items": {"type": "string"}}
    }
}

ENHANCED_OUTPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Enhanced Story Point Estimation Output",
    "type": "object",
    "properties": {
        "story_points": {"type": "integer"},
        "final_score": {"type": "number"},
        "raw_platform_sum": {"type": "number"},
        "integration_adjusted_score": {"type": "number"},
        "risk_detection": {
            "type": "object",
            "properties": {
                "risk_category": {"type": "string"},
                "risk_multiplier": {"type": "number"},
                "detected_keywords": {"type": "array", "items": {"type": "string"}},
                "rationale": {"type": "string"}
            }
        },
        "platform_scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "base_score": {"type": "number"},
                    "adjusted_score": {"type": "number"},
                    "factor_scores": {"type": "object"},
                    "context_adjustment": {"type": "number"},
                    "context_rationale": {"type": "string"}
                }
            }
        },
        "integration_overhead": {
            "type": "object",
            "properties": {
                "platform_count": {"type": "integer"},
                "total_integration_multiplier": {"type": "number"},
                "context_switching_multiplier": {"type": "number"},
                "integration_complexity_multiplier": {"type": "number"}
            }
        },
        "estimated_hours": {
            "type": "object",
            "properties": {
                "min": {"type": "number"},
                "most_likely": {"type": "number"},
                "max": {"type": "number"}
            }
        },
        "confidence": {"type": "number"},
        "rationale": {"type": "array", "items": {"type": "string"}}
    }
}

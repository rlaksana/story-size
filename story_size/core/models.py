from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

# Original Models (for backward compatibility)
class Factors(BaseModel):
    dc: int = Field(..., alias="DC")
    ic: int = Field(..., alias="IC")
    ib: int = Field(..., alias="IB")
    ds: int = Field(..., alias="DS")
    nr: int = Field(..., alias="NR")

class CodeSummary(BaseModel):
    files_estimated: int
    services_touched: List[str]
    db_migrations_estimated: int
    languages_seen: List[str]

class ScoreExplanations(BaseModel):
    dc_explanation: str
    ic_explanation: str
    ib_explanation: str
    ds_explanation: str
    nr_explanation: str

class Estimation(BaseModel):
    story_points: int
    scale: List[int]
    complexity_score: int
    factors: Factors
    confidence: float
    rationale: List[str]
    code_summary: CodeSummary
    score_explanations: ScoreExplanations

# Enhanced Platform-Aware Models
class PlatformRequirement(BaseModel):
    required: bool
    scope: str = Field(..., description="high, medium, low")
    technologies: List[str] = []

class PlatformDetection(BaseModel):
    platform_requirements: Dict[str, PlatformRequirement]
    work_item_type: str = Field(..., description="feature|bugfix|enhancement|refactor|research")
    complexity_level: str = Field(..., description="simple|moderate|complex|very_complex")
    estimated_platforms: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

class PlatformDirectories(BaseModel):
    fe_dir: Optional[Path] = None
    be_dir: Optional[Path] = None
    mobile_dir: Optional[Path] = None
    devops_dir: Optional[Path] = None
    unified_dir: Optional[Path] = None  # For backward compatibility

class PlatformCodeSummary(BaseModel):
    platform: str
    directory: Optional[Path]
    files_estimated: int
    languages_detected: List[str]
    key_files: List[str]
    loc_by_language: Dict[str, int]
    complexity_indicators: Dict[str, Any] = {}
    project_tree: Optional[str] = None  # Hierarchical directory structure for AI context

class EnhancedCodeAnalysis(BaseModel):
    platform_summaries: Dict[str, PlatformCodeSummary]
    total_files: int
    total_languages: List[str]
    cross_platform_dependencies: List[str] = []

# Platform-specific factors
class FrontendFactors(BaseModel):
    ui_complexity: int = Field(ge=1, le=5)
    user_interaction: int = Field(ge=1, le=5)
    performance: int = Field(ge=1, le=5)
    integration: int = Field(ge=1, le=5)
    testing: int = Field(ge=1, le=5)

class BackendFactors(BaseModel):
    business_logic: int = Field(ge=1, le=5)
    database_impact: int = Field(ge=1, le=5)
    api_design: int = Field(ge=1, le=5)
    integration: int = Field(ge=1, le=5)
    security_performance: int = Field(ge=1, le=5)

class MobileFactors(BaseModel):
    platform_complexity: int = Field(ge=1, le=5)
    offline_support: int = Field(ge=1, le=5)
    device_integration: int = Field(ge=1, le=5)
    app_store_requirements: int = Field(ge=1, le=5)
    cross_platform: int = Field(ge=1, le=5)

class DevOpsFactors(BaseModel):
    infrastructure: int = Field(ge=1, le=5)
    automation: int = Field(ge=1, le=5)
    deployment: int = Field(ge=1, le=5)
    monitoring: int = Field(ge=1, le=5)
    security: int = Field(ge=1, le=5)

class PlatformFactors(BaseModel):
    frontend: Optional[FrontendFactors] = None
    backend: Optional[BackendFactors] = None
    mobile: Optional[MobileFactors] = None
    devops: Optional[DevOpsFactors] = None

class PlatformScoreExplanations(BaseModel):
    frontend_explanation: Optional[str] = None
    backend_explanation: Optional[str] = None
    mobile_explanation: Optional[str] = None
    devops_explanation: Optional[str] = None

class PlatformAnalysis(BaseModel):
    platform: str
    factors: Dict[str, int]  # Platform-specific factors
    explanation: str
    recommended_approach: str
    estimated_hours: Dict[str, int]  # {"min": x, "max": y}
    key_components: List[str] = []
    key_challenges: List[str] = []

class CompleteAnalysis(BaseModel):
    platform_detection: PlatformDetection
    platform_analyses: Dict[str, PlatformAnalysis]
    traditional_factors: Optional[Factors] = None  # Keep for backward compatibility
    overall_story_points: int
    platform_story_points: Dict[str, int]
    confidence_score: float
    analysis_timestamp: datetime = Field(default_factory=datetime.now)

    # NEW: Calculation breakdown for transparency
    calculation_breakdown: Optional[Dict[str, Any]] = None  # Raw scores, multipliers, intermediate values

class EnhancedEstimation(BaseModel):
    """Enhanced estimation model that includes both traditional and platform-aware analysis"""
    traditional_estimation: Optional[Estimation] = None  # Backward compatibility
    platform_analysis: CompleteAnalysis
    output_format: str = "enhanced"

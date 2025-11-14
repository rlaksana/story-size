from pydantic import BaseModel, Field
from typing import List, Optional

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

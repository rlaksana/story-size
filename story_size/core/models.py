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

class AuditFootnote(BaseModel):
    scope: str
    memory_ops: List[str]
    logs_touched: List[str]
    websearch: bool
    gating: str

class Estimation(BaseModel):
    story_points: int
    scale: List[int]
    complexity_score: int
    factors: Factors
    confidence: float
    rationale: List[str]
    code_summary: CodeSummary
    audit_footnote: AuditFootnote

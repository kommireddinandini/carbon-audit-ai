from typing import Any, Literal

from pydantic import BaseModel, Field


Status = Literal["VERIFIED", "WARNING", "NEEDS_REVIEW", "NOT_FOUND"]


class CalculationRequest(BaseModel):
    quantity: float = Field(ge=0)
    emission_factor: float = Field(ge=0)


class FactorLookupRequest(BaseModel):
    activity: str
    scope: str
    unit: str
    region: str | None = None
    year: int | None = None


class RecordInput(BaseModel):
    record_id: str | None = None
    source_document: str = "manual"
    source_row: int = 0
    source_page: int | None = None
    activity: str
    quantity: float
    unit: str
    vendor: str | None = None
    region: str | None = None
    year: int | None = None


class AnalyzeRequest(BaseModel):
    records: list[RecordInput] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)


class FactorResult(BaseModel):
    status: Status
    activity: str
    scope: str
    unit: str
    factor: float | None = None
    source: str | None = None
    source_url: str | None = None
    year: int | None = None
    region: str | None = None
    methodology: str | None = None
    factor_type: str | None = None
    reason: str | None = None


class AuditRecord(BaseModel):
    record_id: str
    source_document: str
    source_row: int
    source_page: int | None = None
    activity: str
    scope: str | None = None
    quantity: float
    normalized_quantity: float | None = None
    unit: str
    normalized_unit: str | None = None
    factor: float | None = None
    factor_source: str | None = None
    factor_source_url: str | None = None
    factor_year: int | None = None
    factor_region: str | None = None
    factor_type: str | None = None
    formula: str | None = None
    result_kg_co2e: float | None = None
    status: Status
    message: str | None = None
    evidence: list[str] = Field(default_factory=list)
    classification_confidence: float | None = None
    agent_reasoning: str | None = None
    greenwashing_flags: list[str] = Field(default_factory=list)


class ClaimResult(BaseModel):
    claim: str
    status: Literal["VERIFIED", "WARNING", "UNSUPPORTED", "NEEDS_REVIEW"]
    explanation: str
    missing_evidence: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    records: list[AuditRecord]
    claims: list[ClaimResult]
    summary: dict[str, Any]
    agent: dict[str, Any] = Field(default_factory=dict)
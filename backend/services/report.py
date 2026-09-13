from collections import defaultdict
from uuid import uuid4

from models.schemas import AnalysisResponse, AuditRecord, RecordInput
from tools.audit import create_audit_record
from tools.calculator import calculate_emissions
from tools.classification import classify_activity
from tools.factor_lookup import lookup_factor
from tools.greenwashing import validate_claim
from tools.unit_conversion import normalize_unit
from agents.lyzr_service import get_lyzr_service


def analyze_records(records: list[RecordInput], claims: list[str]) -> AnalysisResponse:
    agent_service = get_lyzr_service()
    compact_records = [record.model_dump() for record in records]
    try:
        agent_result = agent_service.reason(compact_records, claims)
    except Exception as error:
        if "coroutine" in str(error).lower():
            import gc

            gc.collect()
        agent_result = {"mode": "LYZR_ERROR", "reason": str(error), "classifications": [], "claim_flags": [], "narrative": "Live Lyzr reasoning failed; deterministic results are withheld from verified reporting."}
    output: list[AuditRecord] = []
    for input_record in records:
        classification = classify_activity(input_record.activity)
        agent_classification = next((item for item in agent_result.get("classifications", []) if item.get("record_id") == input_record.record_id), {})
        audit = AuditRecord(
            record_id=input_record.record_id or str(uuid4()), source_document=input_record.source_document,
            source_row=input_record.source_row, source_page=input_record.source_page, activity=input_record.activity, scope=classification.scope,
            quantity=input_record.quantity, unit=input_record.unit, status="NEEDS_REVIEW",
            message=classification.evidence,
            classification_confidence=classification.confidence,
            agent_reasoning=agent_classification.get("reasoning"),
        )
        if agent_result.get("mode") == "LYZR_ERROR":
            audit.status = "NEEDS_REVIEW"
            audit.message = agent_result["reason"]
            output.append(audit)
            continue
        if input_record.quantity < 0:
            audit.status = "NEEDS_REVIEW"
            audit.message = "Quantity cannot be negative; calculation rejected."
            output.append(audit)
            continue
        if not classification.scope:
            audit.status = "NEEDS_REVIEW"
            audit.message = classification.evidence
            output.append(audit)
            continue
        factor = lookup_factor(input_record.activity.lower(), classification.scope, input_record.unit, input_record.region, input_record.year)
        audit.factor_year = factor.year
        audit.factor_region = factor.region
        audit.factor_type = factor.factor_type
        if factor.status != "VERIFIED":
            audit.status = factor.status
            audit.message = factor.reason
            output.append(audit)
            continue
        conversion_status, normalized_quantity, conversion_message = normalize_unit(input_record.quantity, input_record.unit, factor.unit)
        if conversion_status != "CONVERTED":
            audit.status = "NEEDS_REVIEW"
            audit.message = conversion_message
            output.append(audit)
            continue
        emissions = calculate_emissions(normalized_quantity, factor.factor or 0)
        audit.normalized_quantity = normalized_quantity
        audit.normalized_unit = factor.unit
        audit.factor = factor.factor
        audit.factor_source = factor.source
        audit.factor_source_url = factor.source_url
        audit.formula = f"{normalized_quantity} {factor.unit} x {factor.factor} kg CO2e/{factor.unit}"
        audit.result_kg_co2e = emissions
        audit.status = "VERIFIED"
        audit.message = f"Classification confidence: {classification.confidence:.0%}."
        output.append(create_audit_record(audit))
    totals = defaultdict(float)
    for record in output:
        if record.status == "VERIFIED" and record.scope:
            totals[record.scope] += record.result_kg_co2e or 0
    claims_output = [validate_claim(claim, [record.model_dump() for record in output]) for claim in claims]
    return AnalysisResponse(
        records=output,
        claims=claims_output,
        summary={
            "total_kg_co2e": round(sum(totals.values()), 6),
            "scope_1_kg_co2e": round(totals["Scope 1"], 6),
            "scope_2_kg_co2e": round(totals["Scope 2"], 6),
            "scope_3_kg_co2e": round(totals["Scope 3"], 6),
            "verified_records": sum(record.status == "VERIFIED" for record in output),
            "needs_review": sum(record.status == "NEEDS_REVIEW" for record in output),
            "missing_factors": sum(record.status == "NOT_FOUND" for record in output),
            "unsupported_claims": sum(claim.status == "UNSUPPORTED" for claim in claims_output),
        },
        agent=agent_result,
    )
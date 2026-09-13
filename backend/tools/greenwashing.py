from models.schemas import ClaimResult


def validate_claim(claim: str, records: list[dict]) -> ClaimResult:
    text = claim.lower()
    total = len(records)
    scopes = {record.get("scope") for record in records if record.get("status") == "VERIFIED"}
    missing = [f"Verified inventory for {scope}" for scope in ("Scope 1", "Scope 2", "Scope 3") if scope not in scopes]
    if any(record.get("status") != "VERIFIED" for record in records):
        missing.append("Resolution of all records with missing factors, invalid units, or review status")
    if "100% carbon neutral" in text or "carbon neutral" in text:
        if not missing and total > 0:
            return ClaimResult(claim=claim, status="WARNING", explanation="The inventory is complete enough for a review, but neutrality requires separate offset or removal evidence.", missing_evidence=["Verified offsets or removals and their certificates"])
        return ClaimResult(claim=claim, status="UNSUPPORTED", explanation="This claim cannot be substantiated by the available inventory.", missing_evidence=missing + ["Verified offsets or removals and their certificates"])
    return ClaimResult(claim=claim, status="NEEDS_REVIEW", explanation="Claim requires evidence review before publication.", missing_evidence=["Claim-specific supporting evidence"])
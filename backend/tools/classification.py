from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    scope: str | None
    confidence: float
    evidence: str


def classify_activity(activity: str) -> Classification:
    text = activity.lower()
    rules = (
        (("electric", "purchased power", "grid"), "Scope 2", 0.96, "Purchased electricity is an indirect energy emission."),
        (("natural gas", "diesel", "petrol", "fuel combustion"), "Scope 1", 0.95, "Fuel combustion controlled by the company is a direct emission."),
        (("freight", "shipping", "air travel", "flight", "business travel", "hotel"), "Scope 3", 0.91, "Value-chain transport or travel is a Scope 3 activity."),
    )
    for keywords, scope, confidence, evidence in rules:
        if any(keyword in text for keyword in keywords):
            return Classification(scope, confidence, evidence)
    return Classification(None, 0.0, "No conservative classification rule matched this activity.")
from decimal import Decimal


CONVERSIONS: dict[tuple[str, str], Decimal] = {
    ("wh", "kwh"): Decimal("0.001"),
    ("mwh", "kwh"): Decimal("1000"),
    ("kg", "tonnes"): Decimal("0.001"),
    ("tonnes", "kg"): Decimal("1000"),
}


def normalize_unit(quantity: float, unit: str, target_unit: str) -> tuple[str, float, str | None]:
    source = unit.strip().lower()
    target = target_unit.strip().lower()
    if source == target:
        return "CONVERTED", float(Decimal(str(quantity))), None
    multiplier = CONVERSIONS.get((source, target))
    if multiplier is None:
        return "NEEDS_REVIEW", float(quantity), f"Unknown conversion from {unit} to {target_unit}."
    return "CONVERTED", float(Decimal(str(quantity)) * multiplier), None
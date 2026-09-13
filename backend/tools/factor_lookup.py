import csv
import os
from pathlib import Path

from models.schemas import FactorResult

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OFFICIAL_PATH = DATA_DIR / "official_factor_registry.csv"
TEST_ONLY_PATH = DATA_DIR / "emission_factors_test_only.csv"


def _normalise(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def lookup_factor(
    activity: str,
    scope: str,
    unit: str,
    region: str | None = None,
    year: int | None = None,
    allow_test_only: bool = False,
) -> FactorResult:
    """Return an exact source-aware match; never substitute region, unit, scope, or year."""
    requested_region = _normalise(region)
    requested_year = year
    candidates = _rows(OFFICIAL_PATH)
    if allow_test_only and os.getenv("CARBON_AUDIT_ENV", "development") == "development":
        candidates += _rows(TEST_ONLY_PATH)
    matches = [
        row for row in candidates
        if _normalise(row["activity"]) == _normalise(activity)
        and _normalise(row["scope"]) == _normalise(scope)
        and _normalise(row["unit"]) == _normalise(unit)
        and _normalise(row["region"]) == requested_region
        and (requested_year is None or int(row["year"]) == requested_year)
    ]
    if not matches:
        electricity = _normalise(activity) == "electricity"
        if electricity and not requested_region:
            return FactorResult(status="NEEDS_REVIEW", activity=activity, scope=scope, unit=unit, reason="Electricity requires an explicit compatible grid or region context.")
        return FactorResult(status="NOT_FOUND", activity=activity, scope=scope, unit=unit, region=region, year=year, reason="No exact factor matched activity, scope, unit, region, and year.")
    row = matches[0]
    try:
        factor = float(row["factor"])
        row_year = int(row["year"])
    except (TypeError, ValueError):
        return FactorResult(status="NEEDS_REVIEW", activity=activity, scope=scope, unit=unit, region=row.get("region"), reason="Factor registry metadata or value is invalid.")
    if factor < 0:
        return FactorResult(status="NEEDS_REVIEW", activity=activity, scope=scope, unit=unit, region=row.get("region"), year=row_year, reason="Factor registry contains a negative value.")
    if row.get("source") == "TEST_ONLY" and not allow_test_only:
        return FactorResult(status="NEEDS_REVIEW", activity=activity, scope=scope, unit=unit, reason="TEST_ONLY factors are disabled outside explicit development tests.")
    return FactorResult(
        status="VERIFIED", activity=activity, scope=scope, unit=unit, factor=factor,
        source=row["source"], source_url=row["source_url"], year=row_year,
        region=row["region"], methodology=row["methodology"], factor_type=row["factor_type"],
    )
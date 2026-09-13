import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from services.report import analyze_records
from services.ingestion import normalize_rows
from models.schemas import RecordInput
from tools.audit import create_audit_record
from tools.calculator import calculate_emissions
from tools.factor_lookup import lookup_factor
from tools.greenwashing import validate_claim
from tools.unit_conversion import normalize_unit


def test_calculator_positive_and_negative_values():
    assert calculate_emissions(12000, 0.42) == 5040
    for quantity, factor in [(-1, 0.4), (1, -0.4)]:
        try:
            calculate_emissions(quantity, factor)
            assert False
        except ValueError:
            pass


def test_factor_lookup_and_unknown_activity():
    result = lookup_factor("electricity", "Scope 2", "kWh", "UK", 2026)
    assert result.status == "VERIFIED"
    assert result.source == "UK Government GHG Conversion Factors 2026"
    assert result.factor_type == "location_based"
    assert lookup_factor("electricity", "Scope 2", "kWh", "UK").status == "VERIFIED"
    assert lookup_factor("mystery process", "Scope 3", "kg", "UK").status == "NOT_FOUND"


def test_unknown_unit_scope_and_invalid_factor():
    assert normalize_unit(2, "furlong", "kWh")[0] == "NEEDS_REVIEW"
    assert lookup_factor("electricity", "Scope 9", "kWh", "UK").status == "NOT_FOUND"
    try:
        calculate_emissions(10, -1)
        assert False
    except ValueError:
        pass


def test_conversion_and_audit_record():
    assert normalize_unit(2, "MWh", "kWh") == ("CONVERTED", 2000.0, None)
    result = analyze_records([RecordInput(source_document="demo.csv", source_row=2, activity="electricity", quantity=100, unit="kWh", region="UK", year=2026)], [])
    record = result.records[0]
    assert record.status == "VERIFIED"
    assert record.result_kg_co2e == 13.096
    assert record.factor_source_url
    assert record.factor_year == 2026
    assert record.factor_region == "UK"
    assert create_audit_record(record).evidence


def test_missing_factor_blocks_calculation():
    result = analyze_records([RecordInput(activity="unknown activity", quantity=10, unit="kg")], [])
    assert result.records[0].status == "NEEDS_REVIEW"
    assert result.records[0].result_kg_co2e is None


def test_region_unit_scope_and_electricity_context_are_strict():
    assert lookup_factor("electricity", "Scope 2", "kWh").status == "NEEDS_REVIEW"
    assert lookup_factor("electricity", "Scope 2", "kWh", "US-CAMX").status == "VERIFIED"
    assert lookup_factor("electricity", "Scope 2", "kWh", "IN").status == "NOT_FOUND"
    assert lookup_factor("electricity", "Scope 2", "therm", "UK").status == "NOT_FOUND"
    assert lookup_factor("electricity", "Scope 1", "kWh", "UK").status == "NOT_FOUND"


def test_test_only_factor_requires_explicit_development_test_opt_in(monkeypatch):
    monkeypatch.setenv("CARBON_AUDIT_ENV", "development")
    result = lookup_factor("road freight", "Scope 3", "tonne-km", "GLOBAL", 2025, allow_test_only=True)
    assert result.status == "VERIFIED"
    assert result.source == "TEST_ONLY"
    assert result.factor_type == "test_only"
    assert lookup_factor("road freight", "Scope 3", "tonne-km", "GLOBAL", 2025).status == "NOT_FOUND"


def test_demo_csv_loads_and_rejects_negative_quantity():
    csv_path = Path(__file__).resolve().parents[2] / "sample_data" / "demo_records.csv"
    rows = normalize_rows(csv_path.name, csv_path.read_bytes())
    result = analyze_records([RecordInput(**row) for row in rows], [])
    assert len(result.records) == 6
    assert result.records[3].activity == "business air travel"
    assert result.records[3].quantity == 2500
    assert result.records[4].status in {"NOT_FOUND", "NEEDS_REVIEW"}
    assert result.records[5].status == "NEEDS_REVIEW"
    assert result.records[5].result_kg_co2e is None


def test_api_upload_processes_demo_csv():
    client = TestClient(app)
    csv_path = Path(__file__).resolve().parents[2] / "sample_data" / "demo_records.csv"
    response = client.post("/api/upload", files={"file": (csv_path.name, csv_path.read_bytes(), "text/csv")})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["records"]) == 6
    assert payload["records"][5]["status"] == "NEEDS_REVIEW"
    assert payload["records"][5]["result_kg_co2e"] is None


def test_greenwashing_claim_is_unsupported_without_evidence():
    claim = validate_claim("Our company is 100% carbon neutral.", []).model_dump()
    assert claim["status"] == "UNSUPPORTED"
    assert claim["missing_evidence"]


def test_api_health_calculate_lookup_and_analyze():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "healthy"
    assert client.post("/api/calculate", json={"quantity": 10, "emission_factor": 0.5}).json()["emissions"] == 5
    assert client.post("/api/lookup-factor", json={"activity": "electricity", "scope": "Scope 2", "unit": "kWh", "region": "UK"}).json()["status"] == "VERIFIED"
    response = client.post("/api/analyze", json={"records": [{"source_document": "demo.csv", "source_row": 1, "activity": "natural gas", "quantity": 2, "unit": "kWh", "region": "UK", "year": 2026}], "claims": []})
    assert response.status_code == 200
    assert response.json()["summary"]["scope_1_kg_co2e"] == 0.40398


def test_end_to_end_sample_analysis():
    result = analyze_records([
        RecordInput(activity="electricity", quantity=100, unit="kWh", region="UK"),
        RecordInput(activity="natural gas", quantity=2, unit="kWh", region="UK"),
        RecordInput(activity="road freight", quantity=1000, unit="tonne-km", region="GLOBAL"),
        RecordInput(activity="unknown activity", quantity=1, unit="kg"),
        RecordInput(activity="electricity", quantity=1, unit="mystery-unit"),
    ], ["Our company is 100% carbon neutral."])
    assert result.summary["verified_records"] == 2
    assert result.summary["missing_factors"] == 1
    assert result.claims[0].status == "UNSUPPORTED"
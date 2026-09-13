import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.lyzr_service import get_lyzr_config
from models.schemas import RecordInput
from services.report import analyze_records
from tools.calculator import calculate_emissions
from tools.factor_lookup import lookup_factor


def test_missing_lyzr_key_is_explicit_local_mode(monkeypatch):
    monkeypatch.setenv("CARBON_AUDIT_ENV", "test")
    monkeypatch.delenv("LYZR_API_KEY", raising=False)
    config = get_lyzr_config()
    assert config.enabled is False
    assert config.mode == "LOCAL_DETERMINISTIC_FALLBACK"
    assert "not configured" in config.reason


def test_live_configuration_is_detected_without_exposing_key(monkeypatch):
    monkeypatch.setenv("CARBON_AUDIT_ENV", "development")
    monkeypatch.setenv("LYZR_API_KEY", "test-key-not-a-secret")
    config = get_lyzr_config()
    assert config.enabled is True
    assert config.mode == "LYZR_LIVE"
    assert config.api_key_configured is True


def test_local_analysis_keeps_agent_separate_from_deterministic_result(monkeypatch):
    monkeypatch.setenv("CARBON_AUDIT_ENV", "test")
    monkeypatch.delenv("LYZR_API_KEY", raising=False)
    result = analyze_records([RecordInput(activity="electricity", quantity=12500, unit="kWh", region="UK", year=2026)], [])
    record = result.records[0]
    assert result.agent["mode"] == "LOCAL_DETERMINISTIC_FALLBACK"
    assert record.status == "VERIFIED"
    assert record.result_kg_co2e == calculate_emissions(12500, lookup_factor("electricity", "Scope 2", "kWh", "UK", 2026).factor)
    assert record.factor_source_url
    assert record.formula


def test_live_agent_tools_are_source_aware(monkeypatch):
    monkeypatch.setenv("LYZR_API_KEY", "test-key-not-a-secret")
    from agents.lyzr_service import _calculate_verified_tool, _lookup_factor_tool

    blocked = _lookup_factor_tool("electricity", "Scope 2", "kWh", None, 2026)
    assert blocked["status"] == "NEEDS_REVIEW"
    checked = _calculate_verified_tool(12500, "electricity", "Scope 2", "kWh", "UK", 2026)
    assert checked["status"] == "VERIFIED"
    assert checked["emissions"] == 1637.0
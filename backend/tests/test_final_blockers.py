from io import BytesIO
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from services.ingestion import normalize_rows


def _pdf_fixture() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 72 720 Td (electricity,12500,kWh) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_dashboard_is_backend_aggregated_and_claims_are_dynamic():
    client = TestClient(app)
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_kg_co2e"] == 1685.4776
    assert payload["summary"]["unsupported_claims"] == 0
    assert payload["records"]


def test_xlsx_and_pdf_ingestion_are_real_and_malformed_pdf_is_rejected():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["activity", "quantity", "unit", "region", "year"])
    sheet.append(["electricity", 12500, "kWh", "UK", 2026])
    output = BytesIO()
    workbook.save(output)
    xlsx_rows = normalize_rows("activity.xlsx", output.getvalue())
    assert xlsx_rows[0]["activity"] == "electricity"
    assert xlsx_rows[0]["quantity"] == 12500

    pdf_rows = normalize_rows("activity.pdf", _pdf_fixture())
    assert pdf_rows[0]["activity"] == "electricity"
    assert pdf_rows[0]["quantity"] == 12500
    assert pdf_rows[0]["unit"] == "kWh"
    assert pdf_rows[0]["source_page"] == 1

    client = TestClient(app)
    malformed = client.post("/api/upload", files={"file": ("broken.pdf", b"not a pdf", "application/pdf")})
    assert malformed.status_code == 422


def test_dashboard_cors_is_configured_not_wildcard():
    client = TestClient(app)
    response = client.options("/api/dashboard", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
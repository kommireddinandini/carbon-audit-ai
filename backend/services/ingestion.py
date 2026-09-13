import csv
import io
from pathlib import Path
from uuid import uuid4


def normalize_rows(filename: str, content: bytes) -> list[dict]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        text = content.decode("utf-8-sig")
        rows = csv.DictReader(io.StringIO(text))
        return [_normalize_row(row, filename, index) for index, row in enumerate(rows, start=1)]
    if suffix in {".xlsx", ".xlsm"}:
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        values = list(sheet.values)
        if not values:
            return []
        headers = [str(value or "").strip() for value in values[0]]
        return [_normalize_row(dict(zip(headers, row)), filename, index) for index, row in enumerate(values[1:], start=2)]
    if suffix == ".txt":
        text = content.decode("utf-8", errors="replace")
        return [_normalize_row({"activity": line, "quantity": "", "unit": ""}, filename, index) for index, line in enumerate(text.splitlines(), start=1) if line.strip()]
    if suffix == ".pdf":
        return _normalize_pdf(filename, content)
    raise ValueError("Unsupported file type. Use CSV, XLSX, or text.")


def _normalize_pdf(filename: str, content: bytes) -> list[dict]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
    except (PdfReadError, ValueError, OSError) as error:
        raise ValueError("Invalid or unreadable PDF file.") from error
    normalized = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for line_number, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            row = _parse_pdf_line(line)
            row["source_page"] = page_number
            normalized.append(_normalize_row(row, filename, page_number))
    if not normalized:
        raise ValueError("PDF contained no extractable activity text.")
    return normalized


def _parse_pdf_line(line: str) -> dict:
    """Parse a conservative `activity, quantity, unit` line from extracted text."""
    parts = [part.strip() for part in line.replace(";", ",").split(",")]
    if len(parts) >= 3:
        try:
            quantity = float(parts[1])
        except ValueError:
            quantity = 0.0
        return {"activity": parts[0], "quantity": quantity, "unit": parts[2]}
    return {"activity": line, "quantity": 0.0, "unit": ""}


def _normalize_row(row: dict, filename: str, index: int) -> dict:
    lowered = {str(key).strip().lower().replace(" ", "_"): value for key, value in row.items()}
    activity = lowered.get("activity") or lowered.get("description") or lowered.get("item") or ""
    quantity = lowered.get("quantity") or lowered.get("amount") or 0
    unit = lowered.get("unit") or lowered.get("units") or ""
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        quantity = 0.0
    return {
        "record_id": str(uuid4()),
        "source_document": filename,
        "source_row": index,
        "source_page": int(lowered["source_page"]) if str(lowered.get("source_page", "")).isdigit() else None,
        "activity": str(activity).strip(),
        "quantity": quantity,
        "unit": str(unit).strip(),
        "vendor": lowered.get("vendor"),
        "region": str(lowered.get("region") or "GLOBAL"),
        "year": int(lowered["year"]) if str(lowered.get("year", "")).isdigit() else None,
    }
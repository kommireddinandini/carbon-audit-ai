import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import AnalyzeRequest, CalculationRequest, FactorLookupRequest, RecordInput
from services.ingestion import normalize_rows
from services.report import analyze_records
from tools.calculator import calculate_emissions
from tools.factor_lookup import lookup_factor
from agents.lyzr_service import get_lyzr_service
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

AUDIT_RECORDS = {}

app = FastAPI(
    title="CarbonAudit AI",
    description="ESG Carbon Accounting & Compliance Agent",
    version="1.0.0",
)
allowed_origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"], allow_credentials=True)


@app.get("/")
def home():
    return {
        "status": "running",
        "message": "CarbonAudit AI backend is running"
    }


@app.get("/health")
def health():
    service = get_lyzr_service()
    return {"status": "healthy", "service": "carbon-audit-api", "agent_mode": service.config.mode, "agent_reason": service.config.reason}


@app.post("/api/calculate")
def calculate(request: CalculationRequest):
    try:
        result = calculate_emissions(request.quantity, request.emission_factor)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"quantity": request.quantity, "factor": request.emission_factor, "emissions": result, "emissions_unit": "kg CO2e"}


@app.post("/api/lookup-factor")
def factor(request: FactorLookupRequest):
    return lookup_factor(request.activity, request.scope, request.unit, request.region, request.year)


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    result = analyze_records(request.records, request.claims)
    for record in result.records:
        AUDIT_RECORDS[record.record_id] = record
    return result


@app.get("/api/dashboard")
def dashboard():
    demo_path = Path(__file__).resolve().parents[1] / "sample_data" / "demo_records.csv"
    try:
        rows = normalize_rows(demo_path.name, demo_path.read_bytes())
        result = analyze_records([RecordInput(**row) for row in rows], [])
        for record in result.records:
            AUDIT_RECORDS[record.record_id] = record
        return result
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Demo dashboard data is unavailable") from error


@app.get("/api/audit/{record_id}")
def audit(record_id: str):
    record = AUDIT_RECORDS.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit record not found")
    return record


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx", ".xlsm", ".txt", ".pdf")):
        raise HTTPException(status_code=415, detail="Supported uploads: CSV, XLSX, XLSM, TXT, PDF")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit")
    try:
        rows = normalize_rows(file.filename, content)
        request = AnalyzeRequest(records=rows)
        result = analyze_records(request.records, request.claims)
        for record in result.records:
            AUDIT_RECORDS[record.record_id] = record
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
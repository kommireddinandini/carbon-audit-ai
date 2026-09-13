# CarbonAudit AI

CarbonAudit AI is an audit-first ESG and carbon accounting copilot. It ingests activity records, classifies emissions into Scope 1/2/3, matches exact emission factors, blocks unsupported calculations, and exposes a traceable evidence chain for every result.

## Architecture

React dashboard -> FastAPI -> one Lyzr agent -> deterministic Python tools -> structured audit result. The tool layer owns ingestion, conservative validation, unit conversion, exact factor lookup, arithmetic, claim validation, and audit objects. The Lyzr agent interprets compact activity context and claims; it cannot provide factors or final arithmetic.

```text
Upload -> normalize -> Lyzr classification/claim reasoning
					  -> deterministic validation
					  -> official factor lookup -> calculator
					  -> audit provenance -> dashboard
```

## Grounding and safety

The source-aware registry in `backend/data/official_factor_registry.csv` contains extracted official rows from the UK Government 2026 flat file and EPA eGRID 2023 subregion data. The original downloadable workbooks are referenced in the registry and kept as local source artifacts. UK factors are scoped to `UK`; eGRID electricity is scoped to an explicit subregion such as `US-CAMX`. They are never used for another region.

Lookup requires exact activity, scope, unit, region, and optional year matches. Electricity without grid context returns `NEEDS_REVIEW`. Missing factors, unknown units, unresolved records, and unsupported claims return review states rather than guesses. `backend/data/emission_factors_test_only.csv` remains available only through an explicit development-test opt-in and is never used by the production-style analysis workflow.

## Setup

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

`LYZR_API_KEY` is required for live Lyzr execution and must never be committed. Without it, local deterministic mode is available for tests and development and is explicitly shown as `Local deterministic mode`, never as a live agent. `LYZR_PROVIDER` defaults to `gpt-4o-mini`. The frontend requires Node.js 18+:

```powershell
cd frontend
npm install
npm run dev
```

In another terminal, start the API:

```powershell
cd backend
..\venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open the Vite URL shown by npm. The dashboard includes synthetic demo records and can upload CSV, XLSX, text, and PDF files (text extraction for PDF is intentionally basic in this MVP).

## API

- `GET /health`
- `POST /api/calculate`
- `POST /api/lookup-factor`
- `POST /api/analyze`
- `POST /api/upload`
- `GET /api/audit/{record_id}`

## Testing

```powershell
venv\Scripts\python.exe -m pytest backend -q
cd frontend
npm run build
```

The tests cover deterministic arithmetic, negative inputs, exact and missing factors, unknown units/scopes, audit creation, API health/calculation/lookup, unsupported claims, and an end-to-end sample analysis.

The Lyzr integration registers official factor lookup, verified calculation, context validation, and audit evidence tools. Numeric outputs are calculated by `backend/tools/calculator.py` after exact factor matching; Lyzr output is treated as reasoning metadata and never as accounting evidence.

## Deployment

Build the frontend with `npm run build` from `frontend/`, then serve `frontend/dist/` with a static web server. Run the API from the repository root with `venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000`. Set `LYZR_API_KEY`, `LYZR_PROVIDER`, `CARBON_AUDIT_ENV`, and a comma-separated `FRONTEND_ORIGIN` in the deployment environment. Keep `.env` outside version control and replace the development/test factor registry with reviewed official source snapshots before production reporting.

##Demo Video
Demo Video: https://youtu.be/KkmWhbQGd3I

## Limitations and next steps

Some UK freight and air-travel categories require more granular activity definitions than the current normalized record provides and therefore remain `NEEDS_REVIEW`. PDF parsing is line-oriented and the current audit store is process-local. Production work should add authenticated persistence, signed source snapshots, and richer document extraction.

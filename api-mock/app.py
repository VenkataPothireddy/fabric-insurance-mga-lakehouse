"""
Mock IMS Insurance API
======================
Stand-in for Vertafore MGA Systems' API. Loads the Phase 1 synthetic CSVs
into memory at startup and serves them as JSON over HTTP.

Purpose:
  The bronze layer must prove it can ingest from APIs, not just files.
  Citadel's real IMS API is not accessible from this prototype, so this
  mock is the API the bronze API-ingestion notebook will call.

Run with:
  uvicorn app:app --reload --port 8000

Then visit http://localhost:8000/docs for the interactive API spec.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data-generation" / "output"
API_VERSION = "v1"
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000

# ---------------------------------------------------------------------------
# Load synthetic data once at startup
# ---------------------------------------------------------------------------

def _load_csv(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Missing source CSV: {path}. "
            f"Run data-generation/generate_data.py first."
        )
    return pd.read_csv(path)

policies_df = _load_csv("policies.csv")
claims_df = _load_csv("claims.csv")
agents_df = _load_csv("agents.csv")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mock IMS API",
    description=(
        "Synthetic stand-in for Vertafore MGA Systems. "
        "Used by the Citadel Fabric prototype to demonstrate API-based ingestion."
    ),
    version=API_VERSION,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _paginate(df: pd.DataFrame, limit: int, offset: int) -> dict:
    total = len(df)
    page = df.iloc[offset : offset + limit]
    # Convert NaN, inf, -inf to None so the JSON encoder doesn't choke.
    # JSON has no concept of NaN or infinity; None serializes as null.
    page = page.replace([np.inf, -np.inf, np.nan], None)
    return {
        "data": page.to_dict(orient="records"),
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": int(total),
            "has_more": offset + limit < total,
        },
    }

def _filter_updated_since(
    df: pd.DataFrame, date_col: str, since: Optional[str]
) -> pd.DataFrame:
    if not since:
        return df
    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid updated_since: {since}. "
                f"Expected ISO 8601 (e.g. 2025-01-01T00:00:00)."
            ),
        )
    return df[pd.to_datetime(df[date_col]) >= since_dt]

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def health():
    return {
        "service": "mock-ims-api",
        "version": API_VERSION,
        "status": "ok",
        "endpoints": ["/policies", "/claims", "/agents"],
    }

@app.get("/policies")
def list_policies(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    updated_since: Optional[str] = None,
    program_code: Optional[str] = None,
):
    df = policies_df
    df = _filter_updated_since(df, "effective_date", updated_since)
    if program_code:
        df = df[df["program_code"] == program_code]
    return _paginate(df, limit, offset)

@app.get("/policies/{policy_id}")
def get_policy(policy_id: str):
    match = policies_df[policies_df["policy_id"] == policy_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
    return match.iloc[0].to_dict()

@app.get("/claims")
def list_claims(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    updated_since: Optional[str] = None,
):
    df = claims_df
    df = _filter_updated_since(df, "report_date", updated_since)
    return _paginate(df, limit, offset)

@app.get("/claims/{claim_id}")
def get_claim(claim_id: str):
    match = claims_df[claims_df["claim_id"] == claim_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return match.iloc[0].to_dict()

@app.get("/agents")
def list_agents(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    return _paginate(agents_df, limit, offset)

@app.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    match = agents_df[agents_df["agent_id"] == agent_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return match.iloc[0].to_dict()
"""Vercel Cron job endpoint for ETL."""

import os
import sys
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException

# Add src to Python path
root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root / "src"))

app = FastAPI()


@app.get("/api/cron/etl")
async def etl_cron(authorization: Annotated[str | None, Header()] = None):
    """
    ETL cron job endpoint. Runs nightly via Vercel Cron.

    This endpoint is protected by Vercel Cron's authorization header.
    """
    # Verify this is called by Vercel Cron
    if authorization:
        expected_token = os.getenv("CRON_SECRET")
        if expected_token and authorization != f"Bearer {expected_token}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    # Import ETL main function
    from mcp_registry_search.etl import main as etl_main

    # Run ETL
    try:
        await etl_main()
        return {"status": "success", "message": "ETL pipeline completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETL failed: {str(e)}")

"""FastAPI application for MCP registry search."""

import os
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mcp_registry_search.search import HybridSearch

app = FastAPI(
    title="MCP Registry Search API",
    description="Semantic search API for Model Context Protocol (MCP) servers",
    version="0.1.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize search engine
search_engine = HybridSearch()


class SearchResponse(BaseModel):
    """Search response model."""

    results: list[dict]
    query: str
    limit: int
    count: int


class ServersResponse(BaseModel):
    """List servers response model."""

    servers: list[dict]
    limit: int
    offset: int
    count: int


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "MCP Registry Search API",
        "version": "0.1.0",
        "endpoints": {
            "/search": "Search MCP servers",
            "/servers": "List all MCP servers",
            "/health": "Health check",
            "/docs": "API documentation",
        },
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/search", response_model=SearchResponse)
def search(
    q: Annotated[str, Query(description="Search query")],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of results")] = 10,
    full_text_weight: Annotated[
        float, Query(ge=0, le=10, description="Weight for full-text search")
    ] = 1.0,
    semantic_weight: Annotated[
        float, Query(ge=0, le=10, description="Weight for semantic search")
    ] = 1.0,
):
    """
    Search MCP servers using hybrid search (full-text + semantic).

    - **q**: Search query string
    - **limit**: Maximum number of results (1-100, default: 10)
    - **full_text_weight**: Weight for full-text search (0-10, default: 1.0)
    - **semantic_weight**: Weight for semantic search (0-10, default: 1.0)
    """
    results = search_engine.search(
        query=q, limit=limit, full_text_weight=full_text_weight, semantic_weight=semantic_weight
    )

    return SearchResponse(results=results, query=q, limit=limit, count=len(results))


@app.get("/servers", response_model=ServersResponse)
def list_servers(
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of results")] = 100,
    offset: Annotated[int, Query(ge=0, description="Number of results to skip")] = 0,
):
    """
    List all MCP servers with pagination.

    - **limit**: Maximum number of results (1-1000, default: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    servers = search_engine.list_all_servers(limit=limit, offset=offset)

    return ServersResponse(servers=servers, limit=limit, offset=offset, count=len(servers))


@app.get("/api/cron/etl")
async def etl_cron(authorization: Annotated[str | None, Header()] = None):
    """
    ETL cron job endpoint. Runs nightly via Vercel Cron.

    This endpoint is protected by Vercel Cron's authorization header.
    """
    # Verify this is called by Vercel Cron
    # Vercel Cron sends a bearer token in the Authorization header
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


def main():
    """Run the API server."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

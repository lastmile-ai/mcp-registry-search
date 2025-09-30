"""Vercel entry point - imports FastAPI app from src package."""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import the FastAPI app
from mcp_registry_search.api import app  # noqa: F401, E402

"""Vercel serverless function entry point."""

import sys
from pathlib import Path

# Add src to Python path  # noqa: E402
root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "src"))

# Import and export the FastAPI app
from mcp_registry_search.api import app  # noqa: E402, F401

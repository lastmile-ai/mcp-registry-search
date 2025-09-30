"""MCP server endpoint for Vercel deployment."""

import sys
from pathlib import Path

# Add src to Python path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "src"))

# Import the FastMCP app
from mcp_registry_search.mcp_server import mcp  # noqa: F401

# Export the MCP app for Vercel
# FastMCP can be run with SSE transport which works with serverless
app = mcp
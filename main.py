"""
MCP Registry Search Server

An MCP server that provides semantic search over the official MCP server registry.
Exposes tools for searching and listing MCP servers using hybrid search (full-text + vector embeddings).
"""

import asyncio

from mcp.server.fastmcp import Context as FastMCPContext
from mcp.server.fastmcp import FastMCP
from mcp_agent.app import MCPApp

from mcp_registry_search.search import HybridSearch

# Create the FastMCP server
mcp = FastMCP(
    name="mcp_registry_search",
    instructions="Search and discover MCP servers from the official registry using semantic and full-text search",
)

# Create the MCPApp
app = MCPApp(
    name="mcp_registry_search",
    description="Semantic search API for the MCP server registry",
    mcp=mcp,
)

# Lazy initialization of search engine
_search_engine = None


async def get_search_engine(ctx: FastMCPContext | None = None):
    """Get or create search engine instance."""
    global _search_engine
    if _search_engine is None:
        import os

        if ctx:
            await ctx.info("Initializing search engine...")

        # Get credentials from app config (which loads from secrets)
        config = app.config
        supabase_url = None
        supabase_key = None
        openai_api_key = None

        # Try to get from config (primary source for deployed apps)
        if hasattr(config, "supabase"):
            supabase_config = config.supabase
            if ctx:
                await ctx.info(f"Config has supabase: {type(supabase_config)}")
            if isinstance(supabase_config, dict):
                supabase_url = supabase_config.get("url")
                supabase_key = supabase_config.get("key")
                if ctx:
                    await ctx.info(
                        f"From config - URL present: {bool(supabase_url)}, KEY present: {bool(supabase_key)}"
                    )
            else:
                # Handle case where it's not a dict (might be a Pydantic model or other object)
                if hasattr(supabase_config, "url"):
                    supabase_url = supabase_config.url
                if hasattr(supabase_config, "key"):
                    supabase_key = supabase_config.key
                if ctx:
                    await ctx.info(
                        f"From config object - URL present: {bool(supabase_url)}, KEY present: {bool(supabase_key)}"
                    )

        if hasattr(config, "openai") and config.openai:
            if hasattr(config.openai, "api_key"):
                openai_api_key = config.openai.api_key
                if ctx:
                    await ctx.info(f"OpenAI key from config: {bool(openai_api_key)}")

        # Fallback to env vars for local development
        if not supabase_url:
            supabase_url = os.getenv("SUPABASE_URL")
            if ctx:
                await ctx.info(f"Using SUPABASE_URL from env: {bool(supabase_url)}")
        if not supabase_key:
            supabase_key = os.getenv("SUPABASE_KEY")
            if ctx:
                await ctx.info(f"Using SUPABASE_KEY from env: {bool(supabase_key)}")
        if not openai_api_key:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if ctx:
                await ctx.info(f"Using OPENAI_API_KEY from env: {bool(openai_api_key)}")

        _search_engine = HybridSearch(
            supabase_url=supabase_url, supabase_key=supabase_key, openai_api_key=openai_api_key
        )

        if ctx:
            await ctx.info("Search engine initialized successfully")
    return _search_engine


@mcp.tool()
async def search_mcp_servers(
    query: str,
    limit: int = 10,
    full_text_weight: float = 1.0,
    semantic_weight: float = 1.0,
    ctx: FastMCPContext | None = None,
) -> list[dict]:
    """
    Search MCP servers using hybrid search (full-text + semantic).

    Args:
        query: Search query string (e.g., "kubernetes", "file system", "weather data")
        limit: Maximum number of results to return (1-100, default: 10)
        full_text_weight: Weight for full-text search (0-10, default: 1.0)
        semantic_weight: Weight for semantic search (0-10, default: 1.0)

    Returns:
        List of server dictionaries with similarity scores
    """
    if ctx:
        await ctx.info(f"Searching MCP registry for: {query}")

    try:
        search_engine = await get_search_engine(ctx)
        results = search_engine.search(
            query=query,
            limit=limit,
            full_text_weight=full_text_weight,
            semantic_weight=semantic_weight,
        )
        if ctx:
            await ctx.info(f"Found {len(results)} results")
        return results
    except Exception as e:
        if ctx:
            await ctx.error(f"Error searching: {str(e)}")
        raise


@mcp.tool()
async def list_mcp_servers(
    limit: int = 100, offset: int = 0, ctx: FastMCPContext | None = None
) -> list[dict]:
    """
    List all MCP servers with pagination.

    Args:
        limit: Maximum number of results to return (1-1000, default: 100)
        offset: Number of results to skip (default: 0)

    Returns:
        List of server dictionaries
    """
    if ctx:
        await ctx.info(f"Listing MCP servers: limit={limit}, offset={offset}")

    try:
        search_engine = await get_search_engine(ctx)
        servers = search_engine.list_all_servers(limit=limit, offset=offset)
        if ctx:
            await ctx.info(f"Successfully retrieved {len(servers)} servers")
        return servers
    except Exception as e:
        if ctx:
            await ctx.error(f"Error listing servers: {str(e)}")
        raise


async def main():
    """Main entry point for local testing."""
    async with app.run():
        # Test search
        print("\n=== Testing Search ===")
        search_results = await search_mcp_servers(query="kubernetes", limit=3)
        print(f"Found {len(search_results)} results:")
        for result in search_results:
            print(f"  - {result['name']} (score: {result.get('similarity_score', 0):.4f})")

        # Test list
        print("\n=== Testing List ===")
        list_results = await list_mcp_servers(limit=5)
        print(f"Found {len(list_results)} servers:")
        for server in list_results:
            print(f"  - {server['name']} v{server['version']}")


if __name__ == "__main__":
    asyncio.run(main())

# To deploy this as an MCP server, run:
# > mcp-agent deploy "mcp_registry_search"

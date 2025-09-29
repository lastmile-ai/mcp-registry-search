"""FastMCP server for MCP registry search."""

import json

from mcp.server.fastmcp import FastMCP

from search import HybridSearch


# Create FastMCP server
mcp = FastMCP(
    "MCP Registry Search",
    instructions="Search and discover MCP servers from the official registry using semantic and full-text search"
)

# Initialize search engine
search_engine = HybridSearch()


@mcp.tool()
def search_mcp_servers(
    query: str,
    limit: int = 10,
    full_text_weight: float = 1.0,
    semantic_weight: float = 1.0
) -> str:
    """
    Search MCP servers using hybrid search (full-text + semantic).

    Args:
        query: Search query string (e.g., "kubernetes", "file system", "weather data")
        limit: Maximum number of results to return (1-100, default: 10)
        full_text_weight: Weight for full-text search (0-10, default: 1.0)
        semantic_weight: Weight for semantic search (0-10, default: 1.0)

    Returns:
        JSON string with search results including server names, descriptions, and metadata
    """
    results = search_engine.search(
        query=query,
        limit=limit,
        full_text_weight=full_text_weight,
        semantic_weight=semantic_weight
    )

    return json.dumps(results, indent=2)


@mcp.tool()
def list_mcp_servers(limit: int = 100, offset: int = 0) -> str:
    """
    List all MCP servers with pagination.

    Args:
        limit: Maximum number of results to return (1-1000, default: 100)
        offset: Number of results to skip (default: 0)

    Returns:
        JSON string with list of all servers
    """
    servers = search_engine.list_all_servers(limit=limit, offset=offset)

    return json.dumps(servers, indent=2)


@mcp.resource("mcp-registry://search/{query}")
def search_resource(query: str) -> str:
    """
    Search MCP servers as a resource.

    Args:
        query: Search query string

    Returns:
        Search results as a formatted string
    """
    results = search_engine.search(query=query, limit=10)

    # Format results as readable text
    output = f"# Search Results for: {query}\n\n"
    for i, result in enumerate(results, 1):
        output += f"## {i}. {result['name']}\n"
        output += f"**Version:** {result['version']}\n"
        output += f"**Description:** {result['description']}\n"
        if result.get('repository'):
            output += f"**Repository:** {result['repository'].get('url', 'N/A')}\n"
        output += f"**Score:** {result.get('similarity_score', 0):.4f}\n\n"

    return output


@mcp.prompt()
def find_mcp_server(task: str) -> str:
    """
    Prompt template to help find the right MCP server for a task.

    Args:
        task: Description of what you want to accomplish

    Returns:
        Prompt to search for relevant MCP servers
    """
    return f"""I need to find an MCP server to help with the following task:

{task}

Please search the MCP registry and recommend the most suitable server(s) for this purpose.
Consider the server's description, capabilities, and how well it matches my requirements."""


if __name__ == "__main__":
    # Run with stdio transport by default
    # Can also use: transport="sse" or transport="streamable-http"
    mcp.run(transport="stdio")
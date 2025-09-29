"""ETL pipeline to fetch and index MCP servers from the registry."""

import asyncio
import os
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from openai import OpenAI
from supabase import Client, create_client

REGISTRY_BASE_URL = "https://registry.modelcontextprotocol.io"


async def fetch_all_servers() -> list[dict[str, Any]]:
    """Fetch all servers from the MCP registry with pagination."""
    servers = []
    cursor = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            url = f"{REGISTRY_BASE_URL}/v0/servers?limit=100"
            if cursor:
                url += f"&cursor={quote(cursor)}"

            print(f"Fetching servers... (cursor: {cursor or 'initial'})")
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            batch = data.get("servers", [])
            servers.extend(batch)

            # Check for next cursor
            metadata = data.get("metadata", {})
            cursor = metadata.get("nextCursor")

            print(f"  Fetched {len(batch)} servers (total: {len(servers)})")

            if not cursor:
                break

    return servers


def filter_active_servers(servers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to only active servers (latest versions only) and extract relevant fields."""
    active_servers = []

    for server in servers:
        # Only include active servers
        if server.get("status") != "active":
            continue

        # Only include latest versions
        meta = server.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
        if not meta.get("isLatest", False):
            continue

        # Extract relevant fields
        active_servers.append(
            {
                "name": server.get("name", ""),
                "description": server.get("description", ""),
                "version": server.get("version", ""),
                "repository": server.get("repository", {}),
                "packages": server.get("packages", []),
                "remotes": server.get("remotes", []),
            }
        )

    return active_servers


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using OpenAI API."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    print(f"Generating embeddings for {len(texts)} servers...")

    # OpenAI allows up to 2048 texts per batch for text-embedding-3-small
    # We'll process in batches of 500 to be safe
    batch_size = 500
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        print(f"  Processing batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")

        response = client.embeddings.create(
            model="text-embedding-3-small", input=batch, encoding_format="float"
        )

        embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(embeddings)

    return all_embeddings


async def upsert_servers_to_supabase(
    supabase: Client, servers: list[dict[str, Any]], embeddings: list[list[float]]
):
    """Upsert servers and embeddings to Supabase."""
    print(f"Upserting {len(servers)} servers to Supabase...")

    # Prepare data for upsert
    rows = []
    for server, embedding in zip(servers, embeddings):
        rows.append(
            {
                "name": server["name"],
                "description": server["description"],
                "version": server["version"],
                "repository": server["repository"],
                "packages": server["packages"],
                "remotes": server["remotes"],
                "embedding": embedding,
            }
        )

    # Upsert in batches (Supabase has a limit)
    batch_size = 100
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        print(f"  Upserting batch {i // batch_size + 1}/{(len(rows) - 1) // batch_size + 1}")

        supabase.table("mcp_servers").upsert(batch, on_conflict="name").execute()

    print("Upsert completed!")


async def main(limit: int | None = None):
    """Run the ETL pipeline.

    Args:
        limit: Optional limit on number of servers to process (for testing)
    """
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

    supabase = create_client(supabase_url, supabase_key)

    # Fetch all servers
    print("Starting ETL pipeline...")
    all_servers = await fetch_all_servers()
    print(f"Fetched {len(all_servers)} total servers")

    # Filter to active servers (latest versions only)
    active_servers = filter_active_servers(all_servers)
    print(f"Filtered to {len(active_servers)} active servers (latest versions)")

    # Apply limit if specified (for testing)
    if limit:
        active_servers = active_servers[:limit]
        print(f"🧪 Test mode: Limited to {limit} servers")

    # Create search texts
    search_texts = [f"{server['name']} {server['description']}" for server in active_servers]

    # Generate embeddings
    embeddings = await generate_embeddings(search_texts)

    # Upsert to Supabase
    await upsert_servers_to_supabase(supabase, active_servers, embeddings)

    print("✅ ETL pipeline completed successfully!")


def cli_main():
    """CLI entry point."""
    load_dotenv()
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()

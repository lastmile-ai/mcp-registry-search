"""Search functionality using Supabase hybrid search."""

import os
from typing import Any

from openai import OpenAI
from supabase import Client, create_client


class HybridSearch:
    """Hybrid search engine using Supabase full-text + vector search."""

    def __init__(self):
        """Initialize the search engine with Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def search(
        self,
        query: str,
        limit: int = 10,
        full_text_weight: float = 1.0,
        semantic_weight: float = 1.0,
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search combining full-text and semantic search.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            full_text_weight: Weight for full-text search (default: 1.0)
            semantic_weight: Weight for semantic search (default: 1.0)

        Returns:
            List of server dictionaries with similarity scores
        """
        # Generate query embedding
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small", input=query, encoding_format="float"
        )
        query_embedding = response.data[0].embedding

        # Call the hybrid_search function in Supabase
        result = self.supabase.rpc(
            "hybrid_search",
            {
                "query_text": query,
                "query_embedding": query_embedding,
                "match_limit": limit,
                "full_text_weight": full_text_weight,
                "semantic_weight": semantic_weight,
            },
        ).execute()

        return result.data

    def list_all_servers(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """
        List all servers with pagination.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of server dictionaries
        """
        result = (
            self.supabase.table("mcp_servers")
            .select("name,description,version,repository,packages,remotes")
            .order("name")
            .range(offset, offset + limit - 1)
            .execute()
        )

        return result.data

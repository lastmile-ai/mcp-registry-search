"""Search functionality using Supabase hybrid search."""

import logging
import os
from typing import Any

from openai import OpenAI
from supabase import Client, create_client

logger = logging.getLogger(__name__)


class HybridSearch:
    """Hybrid search engine using Supabase full-text + vector search."""

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        openai_api_key: str | None = None,
    ):
        """Initialize the search engine with Supabase client.

        Args:
            supabase_url: Supabase URL (falls back to SUPABASE_URL env var)
            supabase_key: Supabase key (falls back to SUPABASE_KEY env var)
            openai_api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
        """
        supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).strip()
        supabase_key = (supabase_key or os.getenv("SUPABASE_KEY", "")).strip()
        openai_api_key = (openai_api_key or os.getenv("OPENAI_API_KEY", "")).strip()

        logger.info(
            f"Initializing HybridSearch with supabase_url={supabase_url[:30] if supabase_url else 'None'}..."
        )
        logger.info(f"SUPABASE_KEY present: {bool(supabase_key)}")
        logger.info(f"OPENAI_API_KEY present: {bool(openai_api_key)}")

        if not supabase_url or not supabase_key:
            logger.error(
                f"Missing credentials - URL: {bool(supabase_url)}, KEY: {bool(supabase_key)}"
            )
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        if not openai_api_key:
            logger.error("Missing OPENAI_API_KEY")
            raise ValueError("OPENAI_API_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.openai_client = OpenAI(api_key=openai_api_key)
        logger.info("HybridSearch initialized successfully")

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
            .select("name,description,version,repository,packages,remotes,status,is_latest")
            .order("name")
            .range(offset, offset + limit - 1)
            .execute()
        )

        return result.data

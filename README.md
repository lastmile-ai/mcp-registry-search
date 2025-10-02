# MCP Registry Search

Semantic search API for MCP servers using the official Model Context Protocol registry.

Use as:
* **REST API (search)**: https://mcp-registry-search.vercel.app/search?q=kubernetes&limit=2
* **REST API (list)**: https://mcp-registry-search.vercel.app/servers?limit=10&offset=0
* **MCP Server (SSE)**: https://mcp-registry-search.vercel.app/api/sse

Cron job reindexes the entire registry every night.

Built with:
* [mcp-agent cloud](https://mcp-agent.com/)
* Supabase
* Vercel

## Usage

### Search REST API

Query the registry using the `/search` endpoint:

**Endpoint:** https://mcp-registry-search.vercel.app/search?q=kubernetes&limit=2

**Example:**
```bash
curl "https://mcp-registry-search.vercel.app/search?q=kubernetes&limit=2"
```

**Example Response:**
```json
{
  "results": [
    {
      "id": 259,
      "name": "io.github.vfarcic/dot-ai",
      "description": "AI-powered development platform for Kubernetes deployments and intelligent automation",
      "version": "0.101.0",
      "repository": {
        "url": "https://github.com/vfarcic/dot-ai",
        "source": "github"
      },
      "packages": [
        {
          "version": "0.101.0",
          "transport": {
            "type": "stdio"
          },
          "identifier": "@vfarcic/dot-ai",
          "registryType": "npm"
        }
      ],
      "remotes": [],
      "similarity_score": 0.606411385574579
    },
    {
      "id": 272,
      "name": "io.github.containers/kubernetes-mcp-server",
      "description": "An MCP server that provides [describe what your server does]",
      "version": "1.0.0",
      "repository": {
        "url": "https://github.com/containers/kubernetes-mcp-server",
        "source": "github"
      },
      "packages": [],
      "remotes": [],
      "similarity_score": 0.451448836663574
    }
  ],
  "query": "kubernetes",
  "limit": 2,
  "count": 2
}
```

**Query Parameters:**
- `q` (required): Search query string
- `limit` (optional): Maximum number of results (default: 10)
- `full_text_weight` (optional): Weight for full-text search (default: 1.0)
- `semantic_weight` (optional): Weight for semantic search (default: 1.0)

### List Servers API

List all servers with pagination using the `/servers` endpoint:

**Endpoint:** https://mcp-registry-search.vercel.app/servers?limit=10&offset=0

**Example:**
```bash
curl "https://mcp-registry-search.vercel.app/servers?limit=5"
```

**Query Parameters:**
- `limit` (optional): Maximum number of results (default: 100)
- `offset` (optional): Number of results to skip (default: 0)

### MCP Server

Connect to the MCP server via SSE for direct integration with MCP clients:

**Endpoint:** https://mcp-registry-search.vercel.app/api/sse

**Available Tools:**
- `search_mcp_servers(query, limit, full_text_weight, semantic_weight)` - Search servers using hybrid search
- `list_mcp_servers(limit, offset)` - List all servers with pagination

**Add to your MCP client config:**
```json
{
  "mcpServers": {
    "registry-search": {
      "url": "https://mcp-registry-search.vercel.app/api/sse",
      "transport": {
        "type": "sse"
      }
    }
  }
}
```

## Features

- 🔍 **Hybrid search** combining lexical (PostgreSQL full-text) and semantic (pgvector) search
- 🚀 **Fast vector similarity** using OpenAI embeddings + Supabase pgvector
- 📊 **Ranked results** using weighted scoring
- 🔄 **Automatic ETL pipeline** to fetch and index MCP servers
- 🌐 **FastAPI REST API** for web access
- 🔌 **FastMCP server** for MCP client integration
- ☁️ **Deployable to Vercel** (FastAPI) and any MCP-compatible host (FastMCP)

## Architecture

```
┌─────────────────┐
│  MCP Registry   │
│   (Source API)  │
└────────┬────────┘
         │
         │ ETL Pipeline
         ↓
┌─────────────────┐
│    Supabase     │
│  (PostgreSQL +  │
│    pgvector)    │
└────────┬────────┘
         │
         │ Search Query
         ↓
┌─────────────────┬─────────────────┐
│   FastAPI REST  │mcp-agent Server │
│      (Web)      │   (MCP Clients) │
└─────────────────┴─────────────────┘
```

## Development

### 1. Install dependencies

```bash
uv sync
```

### 2. Set up Supabase

1. Create a [Supabase account](https://supabase.com)
2. Create a new project
3. Run the SQL in `schema.sql` in the Supabase SQL editor
4. Get your project URL and anon key from Settings > API

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add:
- `OPENAI_API_KEY`: Your OpenAI API key
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key

### 4. Run ETL to fetch and index servers

```bash
uv run etl.py
```

This will:
1. Fetch all servers from the MCP registry
2. Filter to active servers (latest versions only)
3. Generate embeddings using OpenAI
4. Store in Supabase with vector indices

### 5. Start the servers

**FastAPI (REST API):**
```bash
uvicorn api:app --reload
```

API available at `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

**FastMCP (MCP Server):**
```bash
uv run main.py
```

## API Usage

### REST API

**Search servers:**
```bash
curl "http://localhost:8000/search?q=kubernetes&limit=5"
```

**List all servers:**
```bash
curl "http://localhost:8000/servers?limit=100&offset=0"
```

**Health check:**
```bash
curl "http://localhost:8000/health"
```

### MCP Server

The FastMCP server provides:

**Tools:**
- `search_mcp_servers(query, limit, full_text_weight, semantic_weight)` - Search servers
- `list_mcp_servers(limit, offset)` - List all servers

**Resources:**
- `mcp-registry://search/{query}` - Search results as formatted text

**Prompts:**
- `find_mcp_server(task)` - Prompt template to find servers for a task

**Add to your MCP client config:**
```json
{
  "mcpServers": {
    "registry-search": {
      "command": "uv",
      "args": ["run", "main.py"],
      "cwd": "/path/to/mcp-registry-search",
      "env": {
        "OPENAI_API_KEY": "your-key",
        "SUPABASE_URL": "your-url",
        "SUPABASE_KEY": "your-key"
      }
    }
  }
}
```

## Deployment

### Vercel (FastAPI)

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Add environment variables to Vercel:
```bash
vercel env add OPENAI_API_KEY
vercel env add SUPABASE_URL
vercel env add SUPABASE_KEY
vercel env add CRON_SECRET  # Random secret to protect cron endpoint
```

3. Deploy:
```bash
vercel
```

**Automatic ETL Updates:**
The project includes a Vercel Cron job that runs nightly at midnight (UTC) to refresh the server index. The cron job calls `/api/cron/etl` which is protected by the `CRON_SECRET` environment variable.

### Public SSE Proxy (Edge)

Expose an authenticated upstream SSE endpoint publicly by proxying through a Vercel Edge Function that injects the bearer token and streams responses.

1) Configure env vars (in Vercel):
```bash
vercel env add UPSTREAM_SSE_URL   # e.g. https://<host>/sse
vercel env add UPSTREAM_SSE_TOKEN # bearer token for upstream
```

Alternative names supported for the token: `LM_API_KEY` or `LM_API_TOKEN`.

2) Endpoint path
- The SSE proxy is available at `/api/sse` (see `api/sse.ts`).
- The MCP messages proxy is available at `/api/messages` (see `api/messages.ts`).
- Rewrites expose root paths: `/sse` → `/api/sse`, `/messages` → `/api/messages` for MCP clients that expect root-level endpoints.

3) CORS and streaming
- CORS: `Access-Control-Allow-Origin: *`
- Streaming: Edge Runtime streams SSE by default; cache disabled.

4) Example usage
```bash
curl -N https://<your-project>.vercel.app/api/sse
# or using the root rewrite
curl -N https://<your-project>.vercel.app/sse
```

5) Custom upstream per deployment (optional)
- Override with `UPSTREAM_SSE_URL` in env without changing code.
- Messages upstream auto-derives from the SSE URL, or set `UPSTREAM_MESSAGES_URL` explicitly if needed.

### mcp-agent Server
We use [mcp-agent cloud](https://mcp-agent.com) to deploy and host the MCP server. Under the covers, it's a FastMCP server (see [main.py](./main.py)).

To do so yourself, you can run:
* uv run mcp-agent login
* uv run mcp-agent deploy

## Manual ETL Updates

To manually refresh the server index:

**Locally:**
```bash
uv run etl.py
# or
make etl
```

**On Vercel (trigger cron endpoint):**
```bash
curl -X GET https://your-project.vercel.app/api/cron/etl \
  -H "Authorization: Bearer YOUR_CRON_SECRET"
```

The automatic nightly cron job handles updates, but you can manually trigger it anytime.

## Development

**Project structure:**
```
registry/
├── api.py              # FastAPI REST API (hosted on Vercel)
├── main.py             # MCP server (hosted on mcp-agent cloud)
├── search.py           # Search engine
├── etl.py              # ETL pipeline
├── schema.sql          # Supabase schema
├── pyproject.toml      # Dependencies
├── vercel.json         # Vercel config
└── README.md           # This file
```

## License

Apache 2.0

# MCP Registry Search

Semantic search API for MCP (Model Context Protocol) servers using hybrid search (BM25 + embeddings).

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
│   FastAPI REST  │  FastMCP Server │
│      (Web)      │   (MCP Clients) │
└─────────────────┴─────────────────┘
```

## Setup

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
uv run mcp_server.py
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
      "args": ["run", "mcp_server.py"],
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

### FastMCP Server

The FastMCP server can be:
- Run locally and connected via stdio
- Hosted on any server with Python support
- Deployed as an SSE or HTTP endpoint (change `transport` in `mcp_server.py`)

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

## Cost Estimates

**OpenAI Embeddings:**
- ~500 servers × 1536 dimensions = ~$0.01 per full ETL run
- Query embeddings: ~$0.00001 per search

**Supabase:**
- Free tier: 500MB database + 2GB bandwidth
- Should be sufficient for MCP registry (~500 servers)

**Vercel:**
- Free tier: 100GB bandwidth
- Serverless function invocations included

## Development

**Project structure:**
```
registry/
├── api.py              # FastAPI REST API
├── mcp_server.py       # FastMCP server
├── search.py           # Search engine
├── etl.py              # ETL pipeline
├── schema.sql          # Supabase schema
├── pyproject.toml      # Dependencies
├── vercel.json         # Vercel config
└── README.md           # This file
```

## License

Same as parent project (Apache 2.0)
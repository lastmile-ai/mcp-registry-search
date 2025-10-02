-- Enable pgvector extension for vector similarity search
create extension if not exists vector;

-- Create mcp_servers table
create table if not exists mcp_servers (
    id bigserial primary key,
    name text unique not null,
    description text,
    version text,
    repository jsonb,
    packages jsonb,
    remotes jsonb,
    status text,
    is_latest boolean default false,
    search_text text, -- For full-text search
    embedding vector(1536), -- OpenAI text-embedding-3-small dimensions
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- Create index for full-text search
create index if not exists mcp_servers_search_text_idx on mcp_servers using gin(to_tsvector('english', search_text));

-- Create index for vector similarity search (HNSW for fast approximate nearest neighbor)
create index if not exists mcp_servers_embedding_idx on mcp_servers using hnsw (embedding vector_cosine_ops);

-- Create index on name for lookups
create index if not exists mcp_servers_name_idx on mcp_servers(name);

-- Function to automatically update search_text
create or replace function update_search_text()
returns trigger as $$
begin
    new.search_text := new.name || ' ' || coalesce(new.description, '');
    new.updated_at := now();
    return new;
end;
$$ language plpgsql;

-- Trigger to update search_text on insert/update
drop trigger if exists update_search_text_trigger on mcp_servers;
create trigger update_search_text_trigger
    before insert or update on mcp_servers
    for each row
    execute function update_search_text();

-- Drop old function to allow changing return type (safe if re-created below)
drop function if exists hybrid_search(text, vector(1536), integer, double precision, double precision);

-- Function for hybrid search (combines full-text and vector similarity)
create or replace function hybrid_search(
    query_text text,
    query_embedding vector(1536),
    match_limit int default 10,
    full_text_weight double precision default 1.0,
    semantic_weight double precision default 1.0
)
returns table (
    id bigint,
    name text,
    description text,
    version text,
    repository jsonb,
    packages jsonb,
    remotes jsonb,
    status text,
    similarity_score double precision
)
language plpgsql
as $$
begin
    return query
    with semantic_search as (
        select
            mcp_servers.id,
            1 - (mcp_servers.embedding <=> query_embedding) as similarity
        from mcp_servers
        where mcp_servers.embedding is not null
          and coalesce(lower(mcp_servers.status), 'unknown') <> 'deleted'
        order by mcp_servers.embedding <=> query_embedding
        limit match_limit * 3
    ),
    full_text_search as (
        select
            mcp_servers.id,
            ts_rank(to_tsvector('english', mcp_servers.search_text), plainto_tsquery('english', query_text)) as rank
        from mcp_servers
        where to_tsvector('english', mcp_servers.search_text) @@ plainto_tsquery('english', query_text)
          and coalesce(lower(mcp_servers.status), 'unknown') <> 'deleted'
        order by rank desc
        limit match_limit * 3
    )
    select
        mcp_servers.id,
        mcp_servers.name,
        mcp_servers.description,
        mcp_servers.version,
        mcp_servers.repository,
        mcp_servers.packages,
        mcp_servers.remotes,
        mcp_servers.status,
        (
          (coalesce(semantic_search.similarity, 0.0) * semantic_weight +
           coalesce(full_text_search.rank, 0.0) * full_text_weight)
          *
          (
            case lower(coalesce(mcp_servers.status, 'unknown'))
              when 'active' then 1.00
              when 'maintenance' then 0.95
              when 'deprecated' then 0.85
              when 'outdated' then 0.85
              when 'inactive' then 0.70
              when 'deleted' then 0.20
              else 0.90
            end
          )
          * (case when mcp_servers.is_latest then 1.00 else 0.90 end)
        ) as similarity_score
    from mcp_servers
    left join semantic_search on mcp_servers.id = semantic_search.id
    left join full_text_search on mcp_servers.id = full_text_search.id
    where (semantic_search.id is not null or full_text_search.id is not null)
      and coalesce(lower(mcp_servers.status), 'unknown') <> 'deleted'
    order by similarity_score desc
    limit match_limit;
end;
$$;

-- Idempotent alterations for existing databases
alter table if exists mcp_servers add column if not exists status text;
alter table if exists mcp_servers add column if not exists is_latest boolean default false;

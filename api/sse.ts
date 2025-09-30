// Public SSE proxy using Vercel Edge Runtime
// - Injects Authorization header for upstream
// - Streams SSE responses to clients
// - Adds permissive CORS and no-cache headers

export const config = { runtime: "edge" };

const DEFAULT_UPSTREAM =
  "https://v3615xj23gtzj0gkwdbu84z4r2qp948.deployments.mcp-agent.com/sse";

export default async function handler(req: Request): Promise<Response> {
  // Allow overriding upstream via env; default to provided endpoint
  const upstreamUrl = (process.env.UPSTREAM_SSE_URL || DEFAULT_UPSTREAM).trim();
  const token = (
    process.env.UPSTREAM_SSE_TOKEN ||
    // Allow common alternative names for convenience
    process.env.LM_API_KEY ||
    process.env.LM_API_TOKEN ||
    ""
  ).trim();

  // Handle CORS preflight gracefully
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  // Only allow GET for SSE
  if (req.method !== "GET") {
    return new Response("Method Not Allowed", {
      status: 405,
      headers: corsHeaders({ "Allow": "GET" }),
    });
  }

  if (!token) {
    return new Response("Missing UPSTREAM_SSE_TOKEN", {
      status: 500,
      headers: corsHeaders(),
    });
  }

  // Forward client query string to upstream if present
  const incomingUrl = new URL(req.url);
  const targetUrl = new URL(upstreamUrl);
  if (incomingUrl.search) {
    targetUrl.search = incomingUrl.search;
  }

  // Build headers for upstream request
  const headers = new Headers();
  headers.set("Authorization", `Bearer ${token}`);
  // Propagate last-event-id if provided by client
  const lastEventId = req.headers.get("last-event-id");
  if (lastEventId) headers.set("Last-Event-ID", lastEventId);

  // Fetch upstream with streaming enabled (Edge runtime streams by default)
  const upstream = await fetch(targetUrl.toString(), {
    method: "GET",
    headers,
    // Keep connection alive for long-lived SSE
    // Note: Edge runtime manages timeouts; upstream should allow long reads
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(`Upstream error: ${upstream.status}`, {
      status: upstream.status,
      headers: corsHeaders(),
    });
  }

  // Prepare response headers for SSE + CORS
  const outHeaders = corsHeaders({
    "Content-Type": "text/event-stream; charset=utf-8",
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
  });

  // Pass-through streaming body
  return new Response(upstream.body, {
    status: 200,
    headers: outHeaders,
  });
}

function corsHeaders(extra?: Record<string, string>): Headers {
  const h = new Headers({
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Max-Age": "86400",
    ...(extra || {}),
  });
  return h;
}

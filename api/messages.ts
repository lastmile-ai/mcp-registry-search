// Public MCP messages proxy using Vercel Edge Runtime
// - Accepts POST and forwards to upstream `/messages`
// - Injects Authorization header from env
// - Follows redirects (e.g., trailing slash)
// - Handles CORS and OPTIONS

export const config = { runtime: "edge" };

const DEFAULT_MESSAGES_UPSTREAM =
  "https://v3615xj23gtzj0gkwdbu84z4r2qp948.deployments.mcp-agent.com/messages";

export default async function handler(req: Request): Promise<Response> {
  const method = req.method.toUpperCase();

  // CORS preflight
  if (method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  if (method !== "POST") {
    return new Response("Method Not Allowed", {
      status: 405,
      headers: corsHeaders({ Allow: "POST, OPTIONS" }),
    });
  }

  const baseRaw = (process.env.UPSTREAM_MESSAGES_URL || deriveFromSse() || DEFAULT_MESSAGES_UPSTREAM).trim();
  const base = normalizeMessagesUrl(baseRaw);
  const token = (
    process.env.UPSTREAM_SSE_TOKEN || process.env.LM_API_KEY || process.env.LM_API_TOKEN || ""
  ).trim();

  if (!token) {
    return new Response("Missing UPSTREAM_SSE_TOKEN/LM_API_KEY", {
      status: 500,
      headers: corsHeaders(),
    });
  }

  // Preserve query string (e.g., session_id)
  const incoming = new URL(req.url);
  const target = new URL(base);
  if (incoming.search) target.search = incoming.search;

  // Start from incoming headers to preserve MCP-specific headers
  const headers = new Headers(req.headers);
  // Remove hop-by-hop headers that should not be forwarded
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");
  headers.delete("accept-encoding");
  headers.delete("transfer-encoding");
  // Force auth + sane Accept header
  headers.set("Authorization", `Bearer ${token}`);
  const accept = headers.get("accept");
  if (!accept || !/application\/json|text\/event-stream/.test(accept)) {
    headers.set("accept", "application/json, text/event-stream");
  }

  // Buffer the incoming body so it can be resent safely across redirects
  const bodyBuf = await req.arrayBuffer();

  const upstream = await fetch(target.toString(), {
    method: "POST",
    headers,
    body: bodyBuf,
    redirect: "follow",
  });

  const outHeaders = corsHeaders({
    "Cache-Control": "no-store",
    "Content-Type": upstream.headers.get("content-type") || "application/json",
  });
  // Propagate potential session header from upstream
  const sess = upstream.headers.get("mcp-session-id") || upstream.headers.get("Mcp-Session-Id");
  if (sess) outHeaders.set("Mcp-Session-Id", sess);
  // Let browsers read custom headers if they hit this directly
  outHeaders.set("Access-Control-Expose-Headers", "Mcp-Session-Id");

  return new Response(upstream.body, { status: upstream.status, headers: outHeaders });
}

function deriveFromSse(): string | null {
  const sse = (process.env.UPSTREAM_SSE_URL || "").trim();
  if (!sse) return null;
  if (sse.endsWith("/sse")) return sse.slice(0, -4) + "/messages/";
  if (sse.endsWith("/sse/")) return sse.slice(0, -5) + "/messages/";
  return null;
}

function normalizeMessagesUrl(url: string): string {
  try {
    const u = new URL(url);
    // Ensure trailing slash after /messages to avoid 307 redirects on POST
    if (u.pathname.endsWith("/messages")) {
      u.pathname = u.pathname + "/";
    }
    return u.toString();
  } catch {
    // Fallback heuristic if URL() fails
    if (url.endsWith("/messages")) return url + "/";
    return url;
  }
}

function corsHeaders(extra?: Record<string, string>): Headers {
  return new Headers({
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Max-Age": "86400",
    ...(extra || {}),
  });
}

const SPA_INDEXES = [
  { prefix: "/admin/", index: "/admin/index.html" },
  { prefix: "/landlord/", index: "/landlord/index.html" },
  { prefix: "/tenant/", index: "/t/index.html" },
  { prefix: "/t/", index: "/t/index.html" },
];

// Synthesized SPA/redirect responses must never be cached at the CDN. Pages
// Functions otherwise default to `Cache-Control: public, s-maxage=604800`,
// which stale-caches deep links (e.g. /rent/) for a week across redeploys.
const NO_CACHE = { "Cache-Control": "no-cache, must-revalidate" };

function indexResponseWith(indexResponse) {
  return new Response(indexResponse.body, {
    status: 200,
    headers: { ...indexResponse.headers, ...NO_CACHE },
  });
}

async function serveIndex(context, url, indexPath) {
  const indexUrl = new URL(indexPath, url);
  const indexResponse = await context.env.ASSETS.fetch(indexUrl);
  if (indexResponse.ok) {
    return indexResponseWith(indexResponse);
  }
  return context.next();
}

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const path = url.pathname;

  // /rent/* must keep its _redirects 308 (stale-cache canonicalization). Pages
  // serves the root index.html for unmatched paths instead of 404ing, so the
  // per-app fallbacks below are matched explicitly instead of on a 404 status.
  if (path.startsWith("/rent/")) {
    return context.next();
  }

  const app = SPA_INDEXES.find((entry) => path.startsWith(entry.prefix));
  if (app) {
    return serveIndex(context, url, app.index);
  }

  // Root single-page app (landing) — final fallback for every other path.
  return serveIndex(context, url, "/index.html");
}

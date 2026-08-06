const SPA_INDEXES = [
  { prefix: "/rent/admin/", index: "/rent/admin/index.html" },
  { prefix: "/rent/landlord/", index: "/rent/landlord/index.html" },
  { prefix: "/rent/tenant/", index: "/rent/t/index.html" },
  { prefix: "/rent/t/", index: "/rent/t/index.html" },
  { prefix: "/rent/", index: "/rent/index.html" },
];

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const path = url.pathname;

  if (path === "/" || path === "") {
    const target = new URL("/rent/", url);
    return new Response(null, {
      status: 301,
      headers: { Location: target.toString() },
    });
  }

  // Tenant portal deep links (/rent/{landlordUuid}/t/{tenantId}/{viewToken}) —
  // serve the tenant SPA from Pages. Its router (basename /rent) renders the
  // portal from the URL params, so deep links work without touching the API host.
  const tenantLinkRe =
    /^\/rent\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\/t\/[0-9]+\/[0-9a-zA-Z-]+(?:\/.*)?$/;
  if (tenantLinkRe.test(path)) {
    const indexUrl = new URL("/rent/t/index.html", url);
    const indexResponse = await context.env.ASSETS.fetch(indexUrl);
    if (indexResponse.ok) {
      return new Response(indexResponse.body, {
        status: 200,
        headers: indexResponse.headers,
      });
    }
  }

  const response = await context.next();

  if (response.status === 404) {
    const match = SPA_INDEXES.find((app) => path.startsWith(app.prefix));
    if (match) {
      const indexUrl = new URL(match.index, url);
      const indexResponse = await context.env.ASSETS.fetch(indexUrl);
      if (indexResponse.ok) {
        return new Response(indexResponse.body, {
          status: 200,
          headers: indexResponse.headers,
        });
      }
    }
  }

  return response;
}

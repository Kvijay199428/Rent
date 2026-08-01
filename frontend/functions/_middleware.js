const SPA_INDEXES = [
  { prefix: "/rent/admin/", index: "/rent/admin/index.html" },
  { prefix: "/rent/landlord/", index: "/rent/landlord/index.html" },
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

export const apiFetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  let url = input;
  if (typeof url === 'string' && url.startsWith('/api/')) {
    url = `/rent${url}`;
  }

  const response = await fetch(url, init);
  
  if (response.status === 401 || response.status === 403) {
    if (response.headers.get('X-Session-Expired') === '1') {
      const redirectUrl = response.headers.get('X-Redirect-Url');
      if (redirectUrl) {
        window.location.href = redirectUrl;
        return response;
      }
      window.location.reload();
    }
  }
  
  return response;
};

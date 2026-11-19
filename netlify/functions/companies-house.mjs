const API_ROOT = 'https://api.company-information.service.gov.uk';

function reply(statusCode, payload) {
  return {
    statusCode,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      'x-content-type-options': 'nosniff'
    },
    body: JSON.stringify(payload)
  };
}

async function chGet(path, apiKey) {
  const token = Buffer.from(`${apiKey}:`).toString('base64');
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: { authorization: `Basic ${token}`, accept: 'application/json' }
  });
  const raw = await response.text();
  let data = {};
  try { data = raw ? JSON.parse(raw) : {}; } catch { data = { raw }; }
  if (!response.ok) {
    const error = new Error(data?.error || data?.errors?.[0]?.error || `Companies House returned ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

export const handler = async (event) => {
  if (event.httpMethod !== 'GET') return reply(405, { detail: 'Method not allowed' });
  const apiKey = process.env.COMPANIES_HOUSE_API_KEY;
  if (!apiKey) return reply(503, { detail: 'Companies House integration is not configured. Add COMPANIES_HOUSE_API_KEY in Netlify environment variables.' });

  const q = (event.queryStringParameters?.q || '').trim();
  const companyNumber = (event.queryStringParameters?.company_number || '').trim().toUpperCase();

  try {
    if (q) {
      if (q.length < 2 || q.length > 100) return reply(400, { detail: 'Search term must be between 2 and 100 characters.' });
      const result = await chGet(`/search/companies?q=${encodeURIComponent(q)}&items_per_page=20`, apiKey);
      const items = (result.items || []).map((item) => ({
        title: item.title,
        company_number: item.company_number,
        company_status: item.company_status,
        date_of_creation: item.date_of_creation,
        address: item.address || {}
      }));
      return reply(200, { items, total_results: result.total_results ?? items.length, source: 'Companies House public API', retrieved_at: new Date().toISOString() });
    }

    if (!/^[A-Z0-9]{6,10}$/.test(companyNumber)) return reply(400, { detail: 'Enter a valid Companies House company number.' });

    const [company, officersResult, pscResult, filingsResult] = await Promise.all([
      chGet(`/company/${encodeURIComponent(companyNumber)}`, apiKey),
      chGet(`/company/${encodeURIComponent(companyNumber)}/officers?items_per_page=100`, apiKey).catch((e) => ({ items: [], total_results: 0, _unavailable: e.status || true })),
      chGet(`/company/${encodeURIComponent(companyNumber)}/persons-with-significant-control?items_per_page=100`, apiKey).catch((e) => ({ items: [], total_results: 0, _unavailable: e.status || true })),
      chGet(`/company/${encodeURIComponent(companyNumber)}/filing-history?items_per_page=20`, apiKey).catch((e) => ({ items: [], total_count: 0, _unavailable: e.status || true }))
    ]);

    return reply(200, {
      retrieved_at: new Date().toISOString(),
      company,
      officers: { total_results: officersResult.total_results ?? officersResult.items?.length ?? 0, items: officersResult.items || [], unavailable: !!officersResult._unavailable },
      persons_with_significant_control: { total_results: pscResult.total_results ?? pscResult.items?.length ?? 0, items: pscResult.items || [], unavailable: !!pscResult._unavailable },
      filing_history: { total_count: filingsResult.total_count ?? filingsResult.items?.length ?? 0, items: filingsResult.items || [], unavailable: !!filingsResult._unavailable },
      source: 'Companies House public API',
      source_url: `https://find-and-update.company-information.service.gov.uk/company/${companyNumber}`
    });
  } catch (error) {
    const status = error.status === 404 ? 404 : error.status === 429 ? 429 : error.status === 401 || error.status === 403 ? 502 : 502;
    const message = error.status === 404 ? 'No Companies House record was found for that company number.' : error.status === 429 ? 'Companies House rate limit reached. Please wait and try again.' : 'Companies House could not complete the request. Check the API key and try again.';
    return reply(status, { detail: message, upstream_status: error.status || null });
  }
};

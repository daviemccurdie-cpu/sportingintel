SPORTING INTELLIGENCE HUB — NETLIFY + COMPANIES HOUSE DEMO

DEPLOY
1. Deploy this folder (or its ZIP contents) to Netlify using Add new project > Deploy manually.
2. In Netlify: Site configuration > Environment variables, add:
   COMPANIES_HOUSE_API_KEY = your Companies House API key
3. Trigger a new deploy after adding the variable.
4. Open the deployed site and use Discover to search for a UK company.

SECURITY
- The Companies House key is used only by netlify/functions/companies-house.mjs. The function reads `process.env.COMPANIES_HOUSE_API_KEY`.
- Never put the API key in index.html, commit it to GitHub, or share it in chat.
- The browser calls a Netlify Function; it does not call Companies House directly.

WHAT IS CONNECTED
- Live company search (up to 20 results per query), proxied through Netlify Functions.
- Live company profile lookup.
- Current and former officer data returned by Companies House (first 100 entries).
- Persons with significant control (first 100 entries).
- Filing history (first 20 entries).
- The Discover hierarchy uses the returned Companies House officer and PSC data.

LIMITATIONS
- PSC information is not a complete shareholder register.
- Directors/officers are appointments, not proof of ownership.
- Corporate PSCs are not necessarily every company in a wider group. This demo does not recursively crawl all group companies.
- Counterparty edits remain in local browser storage; they are not shared or centrally persisted.
- Sanctions screening and secure Vault exchange are not connected in this Netlify demo.
- Do not treat Companies House data as independently verified beneficial ownership evidence; review filings and source documents.

FINANCIAL INTELLIGENCE EMPHASIS
- Football Capital IQ foregrounds revenue mix, playing wages / turnover, total staff costs / turnover, player trading and transfer working capital, profitability, cash flow, liquidity, debt service and concentration risk.
- All FY values remain blank until supported by audited statements or official filings. Do not populate sample values as facts.
- Ratios: playing wage-to-turnover = playing staff wages / operating revenue; staff-cost ratio = total employee costs / operating revenue; revenue mix = revenue stream / operating revenue.
- Distinguish recurring operating income from transfer profits and exceptional items; show multi-period trends and retain filing/page/currency/accounting basis.

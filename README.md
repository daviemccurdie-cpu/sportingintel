# Sporting Intelligence — Phase 1.5 Railway deployment

This package contains the approved Phase 1.5 interface plus the Phase 1 backend for Companies House lookups, counterparty persistence and operator-uploaded UK Sanctions List screening.

## Included
- Phase 1.5 HTML interface (Capital Intelligence and FinancialsIQ demo workspace included).
- Server-side Companies House API integration. Keep `COMPANIES_HOUSE_API_KEY` in Railway Variables only.
- SQLite persistence for Companies House-linked counterparties.
- UK Sanctions List screening with automatic download of the current official FCDO CSV, persistent local caching, optional operator upload, and name-similarity triage.
- Health endpoint: `/api/health`.

## Railway deployment
1. Replace the contents of the existing GitHub repository with this package and commit/push.
2. Railway will build and deploy from the connected repository.
3. Attach a Railway Volume to the service, mounted at `/data`.
4. Set these Railway Variables:
   - `COMPANIES_HOUSE_API_KEY` = your existing Companies House API key
   - `DATABASE_PATH` = `/data/sporting_intelligence.sqlite3`
   - `SANCTIONS_DATA_PATH` = `/data/uk_sanctions.csv`
   - `SANCTIONS_ADMIN_TOKEN` = a long, unique secret used only by the operator for sanctions CSV upload
5. Deploy and check `/api/health`.
6. Open the app and run a UK sanctions check. If no dataset is cached on the Railway Volume, the backend downloads the current official UK Sanctions List CSV from the FCDO static download endpoint and caches it at `SANCTIONS_DATA_PATH`. An operator can still upload a current official CSV using `SANCTIONS_ADMIN_TOKEN` if required.

## Important operating notes
- The Capital Intelligence workspace includes a researched real-world public-source case: RedBird Capital Partners / AC Milan. Publicly disclosed deal structure and refinancing facts are separated from firm-reported AUM and outstanding private evidence. The other cases are synthetic. FinancialsIQ does not call an AI model and does not connect to ValuBall, Bloomberg, Moody's or S&P. Companies House is connected for registry lookups only; it does not provide the FinancialsIQ analysis in this demo.
- UK sanctions name-similarity results are potential leads only. They are not confirmed matches or a clean-screen certificate; analysts must review identifiers and source records. Screening currently uses name similarity against the UK list only; it is not a complete multi-jurisdiction sanctions, PEP, adverse-media or ownership-control screening solution.
- Counterparty profile edits are saved to SQLite using the Companies House number where available, or an internal `DEMO-<id>` key for demo records.
- This is a private demo build, not production-ready: authentication, access control, audit logging, secure document storage, and tighter CORS/origin restrictions are still required before external users or sensitive real-world data are introduced.
- Never commit API keys or admin tokens to GitHub or put them in the HTML. Configure secrets in Railway Variables.

## Local run
Python 3.11+: `pip install -r requirements.txt`, set environment variables, then run `uvicorn app:app --reload`.

## Explainer page
The staged scrollytelling product explainer is served at `/about.html` and linked from the Hub top bar as “Why Sporting Intelligence”.

## Entity resolution
The counterparty profile includes Companies House search for related legal entities. Candidate ranking uses client-side Levenshtein name similarity and token overlap as an explainable triage score. It is not a legal identity determination; analysts must confirm the relationship using company filings, PSC information, club disclosures or transaction evidence. The top candidate is emphasised and alternatives are visually de-emphasised.


## Phase 1.9 — Football Capital IQ

This release updates `static/index.html` with the Football Capital IQ case library and the global entity-resolution prototype.

### Changes
- Capital Chain / 777 Partners case study is now integrated into Football Capital IQ; no separate top-level case-lab page.
- Replaces synthetic demo cases with eight real-world football finance / ownership case studies:
  1. 777 Partners / A-CAP — capital chain, creditor exposure and collateral disputes.
  2. Portuguese clubs targeted by organised crime — Operation Matrioskas.
  3. Chelsea — offshore football-related payments (investigative reporting; allegations, not a judicial finding).
  4. Newcastle United / PIF — state-linked ownership, control and human-rights scrutiny (not characterised as dirty money).
  5. Fali Ramadani — charges reported by RUSI; current procedural outcome must be independently verified.
  6. Northampton Town / Sixfields — charges reported; not convictions.
  7. Reading FC — stadium collateral and owner-level financial risk, not a money-laundering finding.
  8. RedBird / AC Milan — neutral acquisition-financing transparency case.
- Adds global entity search via public GLEIF API in the browser prototype.
- Keeps Companies House backend and the existing Railway application configuration.

### Deployment notes
- This is a replacement for the Phase 1.7 deployment package, not a migration of the database.
- Preserve existing Railway environment variables and the persistent `/data` volume.
- The GLEIF browser prototype uses the public API directly. Before production, route it through the backend with caching, rate limiting, logging and provider terms review.
- Companies House remains the existing UK registry integration. OpenCorporates is shown as a planned licensed provider and is not called by this release.
- Case studies distinguish facts, reported allegations, charges, regulatory actions and analysis. Do not treat a risk indicator as proof of criminality.


## Phase 2.0 — Football Capital IQ & Secure Document Exchange Vault

### Football Capital IQ
- Repositioned as a research and analytical tool, not only a library of football case studies.
- Search / entity-resolution workflow is now the first interaction at the top of the section.
- Added a multi-year audited-financials workspace for source retrieval and document upload.
- Added a client-configurable credit-risk model with editable factor scores and weighting sliders. The weighted risk score recalculates as users adjust inputs.
- Assessment confidence is displayed separately from risk score. The current preview deliberately shows low confidence because no audited financials are connected or loaded.
- The 777 / A-CAP and other real-world cases remain further down as contextual case studies.

### Secure Document Exchange Vault
- Repositioned as a secure, permissioned transaction document exchange environment.
- Added transaction-room lifecycle, identity verification, e-signature, document security and audit concepts.
- Signicat is shown as the proposed first identity verification integration; DocuSign is shown as a planned e-signature integration.

### Important implementation boundary
This release is a front-end prototype update. It does not yet implement live audited-financial retrieval, financial statement parsing, persistence of client risk-model configurations, secure document storage/transfer, encryption controls, Signicat ID&V or DocuSign e-signature API connections. Those require backend services, provider credentials, security design, data-processing agreements and end-to-end testing. The buttons and file selection in the standalone preview demonstrate intended workflows only; files are not transmitted or stored by the preview.

Keep existing Railway environment variables and persistent `/data` volume. No database migration is included.


## Phase 2.0.1 — urgent visual hotfix
- Fixed dark-mode contrast across headings, navigation, cards, source panels, flow stages, forms, tables, notices and Vault surfaces.
- Active navigation items now use a dark navy treatment with readable white text in dark mode.
- Corrected the fourth methodology stage contrast.
- Vault page navigation now explicitly resets the document scroll position so the Vault title and Request documents action are at the top when the page is opened.
- No backend, database or provider integration changes.


## Phase 2.1 — Football-specific financial metrics
Expanded the FinancialsIQ historical statement view to include:
- Operating revenue split: broadcasting / TV, matchday, commercial / sponsorship, retail / merchandising and other.
- Player trading: transfer proceeds, gross additions, player amortisation and impairment, transfer receivables and payables, net transfer cash position.
- Squad cost base: playing staff wages, non-playing staff wages, total employee benefit expense, wage-to-revenue and staff-cost-to-revenue ratios.
- Profitability and liquidity: operating result before player trading, EBITDA where disclosed, net result, cash, operating cash flow, current assets and current liabilities.
- Debt and liabilities: borrowings, leases, trade payables, deferred income / season-ticket receipts, tax and payroll liabilities, related-party balances, guarantees and net assets.
- Football credit indicators: net debt / EBITDA, interest cover, transfer receivables / total assets, sponsor concentration and broadcasting dependence.
All values remain blank pending verified source filings. Ratios require consistent definitions and normalisation across clubs, leagues and accounting periods.


## Phase 2.1.1 — Vault page layout correction
- Vault page heading is now `05 / VAULT` with the title `Document and Private Data Exchange Vault`.
- The primary `Request docs` action is aligned in the page header at the top.
- Removed the duplicate create-exchange button from the introductory hero.
- Removed the identity-verification / e-signature integrations panel from the Vault page as requested.
- Fact / Report / Hypothesis / Verified methodology remains in Football Capital IQ and is not part of the Vault page.
- Added an explicit scroll-to-header action when opening Vault Connections.
- No backend, database or provider integration changes.

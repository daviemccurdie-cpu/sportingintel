# Sporting Intelligence Hub — Phase 2.2.2 deployment

This release carries forward the Phase 2.1.1 hub and the Phase 2.2 counterparty-profile improvements, with a critical generated-profile JavaScript syntax fix, a working explainer route/link, and removal of the unwanted methodology panel.

## Contents
- `app.py` — FastAPI backend
- `static/index.html` — Sporting Intelligence Hub front end (Phase 2.2.2)
- `static/about.html` — approved Why Sporting Intelligence explainer
- `uk_sanctions.csv` — bundled UK Sanctions List dataset fallback
- `requirements.txt`, `Procfile` — Railway runtime configuration

## Deploy to Railway
1. Back up the current GitHub repository contents before replacing them.
2. Replace the repository contents with the contents of this ZIP (the files inside the ZIP root, not the enclosing folder).
3. Commit and push to the branch connected to Railway.
4. Keep the existing Railway persistent volume mounted at `/data`.
5. Preserve the existing Railway environment variables and secret values:
   - `DATABASE_PATH=/data/sporting_intelligence.sqlite3`
   - `SANCTIONS_DATA_PATH=/data/uk_sanctions.csv`
   - `SANCTIONS_ADMIN_TOKEN` (existing secret)
   - `COMPANIES_HOUSE_API_KEY` (existing secret)
6. Wait for the Railway deployment to finish, then verify:
   - `/api/health`
   - `/api/sanctions/status`
   - `/about.html`
   - `/` (main hub)

Do not paste secret values into GitHub or this README. Do not remove or recreate the `/data` volume.

## Release checks performed
- Python syntax compilation of `app.py`
- FastAPI import and route registration
- HTTP smoke tests for `/`, `/about.html`, `/api/health`, `/api/sanctions/status`
- Counterparty API PUT/GET persistence smoke test using a temporary test database
- UK sanctions CSV load check (6,449 designation records in the bundled dataset)
- Main hub and explainer JavaScript syntax checks
- Generated full-counterparty page extracted from the live `openFullRecord()` template and its JavaScript syntax-checked
- Confirmed the generated counterparty page contains five tabs and matching pane IDs
- Confirmed the Why SI link points to `/about.html`
- Confirmed the unwanted “Method: fact, report, hypothesis, verification” panel is removed

## Important limitations
- This remains a demo environment, not a production compliance platform.
- Sanctions screening is UK-list name-similarity screening. Potential matches require human identity resolution; no potential match is not a clean-screen certificate.
- Companies House lookups require the existing API key.
- Financial intelligence, adverse media, PEP screening and licensed data-provider integrations are not connected unless separately configured.
- The Vault front end is illustrative; secure document exchange, identity verification, e-signature, production authentication, role-based access control, and a complete audit trail are not implemented by this package.
- Browser-local drafts are not a substitute for shared server persistence. Saved counterparty records use the API/database.

## Rollback
If the deployment fails, roll back to the previous known-good Git commit in GitHub/Railway. Keep the persistent `/data` volume and environment variables unchanged.


## Phase 2.2.2 — Companies House relationship hierarchy
- Discover now renders a relationship hierarchy immediately after a live Companies House company record is selected.
- Toggle directors/officers, PSC/shareholder disclosures, and corporate/group entities independently.
- The graph is driven by the returned Companies House officer and PSC records; adding the selected party to Counterparties retains those registry records in its companyHouse snapshot.
- Important: Companies House PSC data is not a complete shareholder register. Directors are not necessarily owners. Corporate PSC entries are shown as disclosed corporate control links, not assumed group subsidiaries.

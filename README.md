# Sporting Intelligence — Demo release (as-is)

This release packages the reviewed Phase 2.1.1 Hub interface, the updated Why Sporting Intelligence explainer, the existing Companies House / counterparty backend, and the supplied UK Sanctions List CSV.

## Contents
- `static/index.html` — reviewed Sporting Intelligence Hub interface.
- `static/about.html` — latest approved explainer preview (v3).
- `app.py` — existing backend, including Companies House lookup, counterparty persistence and UK sanctions screening.
- `uk_sanctions.csv` — supplied UK Sanctions List export (report date: 17-Nov-2026).
- `requirements.txt`, `Procfile`, `.env.example` — Railway runtime files.

## Deploy to the existing Railway service
1. Replace the contents of the connected GitHub repository with the contents of this package and commit/push to the deployment branch. Railway should then build from GitHub.
2. Preserve the existing Railway persistent volume mounted at `/data`.
3. Preserve / set these Railway Variables:
   - `COMPANIES_HOUSE_API_KEY` — existing private Companies House key.
   - `DATABASE_PATH=/data/sporting_intelligence.sqlite3`
   - `SANCTIONS_DATA_PATH=/data/uk_sanctions.csv`
   - `SANCTIONS_ADMIN_TOKEN` — existing private admin token (or set a new strong secret).
4. The sanctions screening code prefers `/data/uk_sanctions.csv`; if that file is absent, it reads the bundled `uk_sanctions.csv` in the release package. Thus the supplied list is included for the demo even if the persistent-volume copy has not yet been populated. An operator upload/refresh writes to the configured persistent-volume path.
5. After Railway reports a successful deployment, verify `/api/health`, `/api/sanctions/status`, and the `/about.html` page.

## Sanctions dataset
The bundled file is the supplied UK Sanctions List CSV, report date 17-Nov-2026. Screening results are name-similarity leads only, not confirmed matches and not a clean-screen certificate. Analysts must review identifiers, aliases and source records. This is UK-list-only name screening, not comprehensive multi-jurisdiction sanctions, PEP, adverse-media or ownership/control screening.

## Demo limitations — please do not present these as live capabilities
This is an as-is demo release, not production-ready. The front-end demonstrates workflows. Secure document storage/transfer, access controls, authentication, audit logging, encryption controls, Signicat identity verification, DocuSign e-signature, live audited-financial retrieval and AI-driven financial analysis are not implemented as live services. Companies House is connected for registry lookups only. Financial values remain blank pending verified source filings. Do not enter real confidential client data or treat the demo as a production compliance control.

## Existing data and configuration
Keep the Railway `/data` volume and existing environment variables. No database migration is included. Do not commit API keys or admin tokens.

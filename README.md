# Sporting Intelligence — Phase 1.5 Railway deployment

This package contains the approved Phase 1.5 interface plus the Phase 1 backend for Companies House lookups, counterparty persistence and operator-uploaded UK Sanctions List screening.

## Included
- Phase 1.5 HTML interface (Capital Intelligence and FinancialsIQ demo workspace included).
- Server-side Companies House API integration. Keep `COMPANIES_HOUSE_API_KEY` in Railway Variables only.
- SQLite persistence for Companies House-linked counterparties.
- Operator-only UK Sanctions List CSV upload and name-similarity triage.
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
6. In the app's sanctions administration area, upload the official FCDO UK Sanctions List CSV using the admin token. The CSV is not bundled in this ZIP.

## Important operating notes
- The Phase 1.5 Capital Intelligence / FinancialsIQ cases are synthetic demonstrations. They do not call an AI model and do not connect to ValuBall, Bloomberg, Moody's or S&P. Companies House is connected for registry lookups only; it does not provide the FinancialsIQ analysis in this demo.
- UK sanctions name-similarity results are potential leads only. They are not confirmed matches or a clean-screen certificate; analysts must review identifiers and source records.
- Counterparty database persistence currently covers records with a Companies House company number. Other profile edits may remain browser-local until broader persistence is implemented.
- This is a private demo build, not production-ready: authentication, access control, audit logging, secure document storage, and tighter CORS/origin restrictions are still required before external users or sensitive real-world data are introduced.
- Never commit API keys or admin tokens to GitHub or put them in the HTML. Configure secrets in Railway Variables.

## Local run
Python 3.11+: `pip install -r requirements.txt`, set environment variables, then run `uvicorn app:app --reload`.

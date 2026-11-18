# Sporting Intelligence — Phase 1 (live Companies House)

This is a private demo starter. It adds a FastAPI backend that calls the official Companies House API server-side, keeping the API key out of the browser.

## Included
- Live company search: `GET /api/companies/search?q=West Bromwich Albion`
- Company enrichment: `GET /api/companies/{company_number}`
- Company profile, officers, persons with significant control (PSC), and recent filing metadata.
- Health check: `GET /api/health`
- Existing Sporting Intelligence interface in `static/index.html`.

## Prerequisites
- Python 3.11+
- A Companies House API key from https://developer.company-information.service.gov.uk/
- A hosting account (recommended: Railway for the first private demo)

## Run locally
1. Copy `.env.example` to `.env` and add your API key.
2. Install dependencies: `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\\Scripts\\activate`)
3. `pip install -r requirements.txt`
4. Set the environment variable before starting:
   - macOS/Linux: `export COMPANIES_HOUSE_API_KEY="your-key"`
   - PowerShell: `$env:COMPANIES_HOUSE_API_KEY="your-key"`
5. `uvicorn app:app --reload`
6. Open http://127.0.0.1:8000

## Deploy to Railway (recommended demo host)
1. Create a private GitHub repository and upload this folder.
2. In Railway, create a project from that repository.
3. Add the variable `COMPANIES_HOUSE_API_KEY` in Railway's service Variables panel.
4. Deploy. Railway detects the `Procfile`; if needed set the start command to `uvicorn app:app --host 0.0.0.0 --port $PORT`.
5. Keep the service private or protect it with authentication before inviting demo users.

## API key safety
Never put the key in HTML, JavaScript, a public Git repository, or a browser request. If a key has already been shared in a chat, screenshot, or source file, rotate it before deployment. The backend uses HTTP Basic authentication to Companies House, with the API key as the username and an empty password.

## Current limitations / deliberate scope
- Phase 1 retrieves public company profile, officer appointments, PSC records and filing-history metadata.
- Accounts documents themselves may require document API retrieval and parsing; this starter returns filing metadata first.
- The UI must distinguish PSC register entries from ultimate beneficial ownership conclusions.
- No sanctions, PEP, adverse-media, DarkSkreen or screening provider is connected in this phase.
- Search results are not automatically treated as the correct club entity: the operator chooses the matching company number.
- The initial backend has permissive CORS for local demo convenience. Tighten allowed origins and add user authentication before external access.
- No production-grade audit logging, persistence, role-based access or encrypted document store is included yet.

## Phase 1.1 visual and UK sanctions update
- Updated light palette: brighter neutral off-white, deeper separators, stronger navy/teal/green accents and reduced orange dominance.
- DarkSkreen Deep Research now uses a gradient outline rather than a filled gradient.
- Added a persistent Bloomberg-inspired dark-mode toggle in the interface (visual theme only; no separate data mode).
- Added UK Sanctions List endpoints:
  - `POST /api/sanctions/refresh` downloads the official FCDO CSV into the local SQLite cache.
  - `GET /api/sanctions/status` reports dataset count and refresh time.
  - `GET /api/sanctions/check?q=NAME` performs a name-similarity check against the cached list.
- When the Sanctions checkbox is selected for a live company record, the UI attempts a dataset refresh if no local copy exists, then runs the name check.

### Sanctions data caveats
The dataset is the official UK Sanctions List published by FCDO, not the discontinued OFSI Consolidated List. The FCDO page says UKSL became the single source for UK sanctions designations from 28 January 2026. This implementation uses the published CSV and a basic string-similarity screen. It is a triage aid only: possible matches require analyst review against identifiers, aliases, dates of birth, addresses and the underlying designation. A no-name-match result is not a clean bill of health. Refresh the list regularly and do not use this prototype as the sole basis for compliance decisions.

### Deploying this update
Replace the files in the GitHub repository with the updated package contents and commit/push. Railway should then build and deploy from the connected repository. No additional Railway variable is required for UK sanctions; the backend downloads the public FCDO CSV when needed. For reliable persistence between deploys, attach a Railway Volume and set `DATABASE_PATH` to a file path on that mounted volume (for example `/data/sporting_intelligence.sqlite3`).


## Phase 1.2 UI and screening fixes
- Dark mode now forces readable near-white text on near-black surfaces, including page headings and form controls.
- Light theme uses a cleaner, brighter neutral with stronger borders and restrained navy/teal signal colours.
- DarkSkreen Deep Research is a compact gradient-outline control aligned with the other optional checkboxes.
- Counterparties created manually from the portfolio/network workflow are inserted at the top of the in-memory list.
- Full record is now an editable workspace with contact fields, analyst notes, verification notes, analyst-entered review status, Companies House refresh action, UK sanctions check action, and a transparent information-completeness dial.
- The dial is explicitly not a creditworthiness or risk score. Its initial prototype formula gives equal weight to eight populated fields. Edits are stored in browser localStorage for the demo; they are not yet synchronised to the server database.
- UK sanctions CSV parser now detects common delimiters and a wider set of name columns. If the FCDO URL returns a non-CSV response or changes its schema, it reports that explicitly rather than claiming no match.

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

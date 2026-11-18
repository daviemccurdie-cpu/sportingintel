import os, base64, sqlite3, json
from datetime import datetime, timezone
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

API_KEY=os.getenv("COMPANIES_HOUSE_API_KEY","").strip()
CH_BASE="https://api.company-information.service.gov.uk"
app=FastAPI(title="Sporting Intelligence Phase 1 API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

def auth():
    if not API_KEY:
        raise HTTPException(503, "Companies House API key is not configured. Add COMPANIES_HOUSE_API_KEY to the server environment.")

async def ch_get(path: str, params: dict | None=None):
    auth()
    token=base64.b64encode(f"{API_KEY}:".encode()).decode()
    async with httpx.AsyncClient(timeout=25) as client:
        r=await client.get(CH_BASE+path, params=params, headers={"Authorization":f"Basic {token}", "Accept":"application/json"})
    if r.status_code == 404: raise HTTPException(404, "Companies House record not found.")
    if r.status_code == 429: raise HTTPException(429, "Companies House rate limit reached. Please retry shortly.")
    if r.status_code >= 400: raise HTTPException(502, f"Companies House returned HTTP {r.status_code}.")
    return r.json()


DB_PATH=os.getenv("DATABASE_PATH","sporting_intelligence_demo.sqlite3")
class CounterpartyIn(BaseModel):
    company_number: str
    record: dict[str, Any]

def db():
    con=sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS counterparties (company_number TEXT PRIMARY KEY, record_json TEXT NOT NULL, created_at TEXT NOT NULL)")
    return con

@app.get("/api/counterparties")
async def list_counterparties():
    con=db()
    rows=con.execute("SELECT record_json FROM counterparties ORDER BY created_at DESC").fetchall()
    con.close()
    return {"items":[json.loads(row[0]) for row in rows]}

@app.post("/api/counterparties")
async def save_counterparty(payload: CounterpartyIn):
    con=db()
    con.execute("INSERT OR REPLACE INTO counterparties(company_number,record_json,created_at) VALUES(?,?,?)",
      (payload.company_number,json.dumps(payload.record),stamp()))
    con.commit(); con.close()
    return {"saved":True,"company_number":payload.company_number}

def stamp():
    return datetime.now(timezone.utc).isoformat()

@app.get("/api/health")
async def health():
    return {"status":"ok","companies_house_configured":bool(API_KEY),"service":"Sporting Intelligence Phase 1"}

@app.get("/api/companies/search")
async def search_companies(q: str=Query(min_length=2), items_per_page: int=Query(10,ge=1,le=20)):
    data=await ch_get("/search/companies", {"q":q,"items_per_page":items_per_page})
    return {"query":q,"retrieved_at":stamp(),"total_results":data.get("total_results",0),"items":[
        {"company_number":x.get("company_number"),"title":x.get("title"),"company_status":x.get("company_status"),
         "company_type":x.get("company_type"),"address":x.get("address"),"date_of_creation":x.get("date_of_creation"),
         "sic_codes":x.get("sic_codes"),"description":x.get("description"),"links":x.get("links",{})}
        for x in data.get("items",[])
    ]}

@app.get("/api/companies/{company_number}")
async def company_record(company_number: str):
    if not company_number or not company_number.isalnum(): raise HTTPException(400,"Invalid company number.")
    profile, officers, psc, filings = await __import__("asyncio").gather(
        ch_get(f"/company/{company_number}"),
        ch_get(f"/company/{company_number}/officers",{"items_per_page":100}),
        ch_get(f"/company/{company_number}/persons-with-significant-control",{"items_per_page":100}),
        ch_get(f"/company/{company_number}/filing-history",{"items_per_page":20})
    )
    return {
      "retrieved_at":stamp(),
      "company":profile,
      "officers":{"total_results":officers.get("total_results",0),"items":officers.get("items",[])},
      "persons_with_significant_control":{"total_results":psc.get("total_results",0),"items":psc.get("items",[])},
      "filing_history":{"total_count":filings.get("total_count",0),"items":filings.get("items",[])},
      "source":"Companies House public API",
      "source_url":f"https://find-and-update.company-information.service.gov.uk/company/{company_number}"
    }

@app.get("/api/companies/{company_number}/filing-document/{document_id}")
async def filing_document(company_number: str, document_id: str):
    # Filing document content is served by the separate Companies House document API.
    return {"message":"Document retrieval is not included in Phase 1; filing metadata and official document links are returned in the filing history.","company_number":company_number,"document_id":document_id}

# Serve the prototype when placed in ./static
if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

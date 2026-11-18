import os, base64, sqlite3, json, csv, io, re, difflib
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


UKSL_CSV_URL = "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv"

def sanctions_db():
    con=db()
    con.execute("CREATE TABLE IF NOT EXISTS uk_sanctions (uid TEXT PRIMARY KEY, names_json TEXT NOT NULL, data_json TEXT NOT NULL)")
    con.execute("CREATE TABLE IF NOT EXISTS sanctions_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return con

@app.get("/api/sanctions/status")
async def sanctions_status():
    con=sanctions_db()
    count=con.execute("SELECT COUNT(*) FROM uk_sanctions").fetchone()[0]
    row=con.execute("SELECT value FROM sanctions_meta WHERE key='refreshed_at'").fetchone()
    con.close()
    return {"source":"UK Sanctions List (FCDO)","entries_loaded":count,"refreshed_at":row[0] if row else None,"source_url":UKSL_CSV_URL}

@app.post("/api/sanctions/refresh")
async def sanctions_refresh():
    # Download only from the official FCDO static CSV URL.
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        r=await client.get(UKSL_CSV_URL,headers={"User-Agent":"SportingIntelligenceDemo/0.1"})
    if r.status_code != 200:
        raise HTTPException(502,f"FCDO UK Sanctions List download failed (HTTP {r.status_code}). Existing cached list, if any, has been retained.")
    try:
        textdata=r.content.decode('utf-8-sig',errors='replace')
        if textdata.lstrip().lower().startswith(('<!doctype html','<html')):
            raise ValueError("The official download returned an HTML page rather than CSV data. The FCDO download URL or access response may have changed.")
        try:
            dialect=csv.Sniffer().sniff(textdata[:8192], delimiters=',;\\t|')
        except Exception:
            dialect=csv.excel
        reader=csv.DictReader(io.StringIO(textdata), dialect=dialect)
        if not reader.fieldnames: raise ValueError("CSV header row missing")
        headers={str(k or '').strip().lower():str(k or '').strip() for k in reader.fieldnames}
        name_fields=[original for lower,original in headers.items() if re.search(r'name|alias|aka|former|spelling|also known',lower)]
        rows=[]
        for idx,row in enumerate(reader):
            clean={str(k or '').strip():str(v or '').strip() for k,v in row.items() if k}
            names=[]
            for k in name_fields:
                v=clean.get(k,'')
                if v and v.lower() not in ('na','n/a','none','-','null'): names.append(v)
            # UKSL formats may label the primary designation in entity/person name columns.
            if not names:
                for k,v in clean.items():
                    kl=k.lower()
                    if v and re.search(r'^(name|entity name|individual name|ship name)(?:[ _-]?\\d+)?$',kl):
                        names.append(v)
            if not names:
                continue
            uid=next((v for k,v in clean.items() if re.search(r'unique.*id|^id$|group.*id',k,re.I) and v),str(idx))
            rows.append((uid+'-'+str(idx),json.dumps(list(dict.fromkeys(names))),json.dumps(clean)))
        if not rows: raise ValueError("CSV was downloaded, but no rows with recognised designation-name columns were found. Headers received: "+", ".join(reader.fieldnames[:30]))
    except Exception as e:
        raise HTTPException(502,f"Could not parse the official UK Sanctions CSV: {e}")
    con=sanctions_db()
    con.execute("DELETE FROM uk_sanctions")
    con.executemany("INSERT OR REPLACE INTO uk_sanctions(uid,names_json,data_json) VALUES(?,?,?)",rows)
    con.execute("INSERT OR REPLACE INTO sanctions_meta(key,value) VALUES('refreshed_at',?)",(stamp(),))
    con.execute("INSERT OR REPLACE INTO sanctions_meta(key,value) VALUES('source_url',?)",(UKSL_CSV_URL,))
    con.commit(); con.close()
    return {"refreshed":True,"entries_loaded":len(rows),"refreshed_at":stamp(),"source":"UK Sanctions List (FCDO)","source_url":UKSL_CSV_URL}

@app.get("/api/sanctions/check")
async def sanctions_check(q: str=Query(min_length=2), threshold: float=Query(0.84,ge=0.5,le=1.0)):
    con=sanctions_db()
    count=con.execute("SELECT COUNT(*) FROM uk_sanctions").fetchone()[0]
    if not count:
        con.close()
        raise HTTPException(503,"UK sanctions dataset has not been loaded. Call POST /api/sanctions/refresh first.")
    rows=con.execute("SELECT names_json,data_json FROM uk_sanctions").fetchall()
    meta=con.execute("SELECT value FROM sanctions_meta WHERE key='refreshed_at'").fetchone()
    con.close()
    query=re.sub(r'[^a-z0-9 ]',' ',q.lower()); query=' '.join(query.split())
    matches=[]
    for names_json,data_json in rows:
        names=json.loads(names_json); best=0; matched=''
        for name in names:
            candidate=re.sub(r'[^a-z0-9 ]',' ',' '.join(name.lower().split())); candidate=' '.join(candidate.split())
            score=difflib.SequenceMatcher(None,query,candidate).ratio()
            if query==candidate: score=1.0
            elif query in candidate or candidate in query: score=max(score,0.90)
            if score>best: best,matched=score,name
        if best>=threshold:
            data=json.loads(data_json)
            matches.append({"matched_name":matched,"similarity":round(best,3),"record":data})
    matches.sort(key=lambda x:x['similarity'],reverse=True)
    return {"query":q,"source":"UK Sanctions List (FCDO)","refreshed_at":meta[0] if meta else None,"dataset_entries":count,"potential_matches":matches[:20],"match_threshold":threshold,"disclaimer":"Name similarity is a screening lead, not confirmation of identity or a confirmed sanctions hit. Review identifiers and source record before any decision."}

# Serve the prototype when placed in ./static
if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

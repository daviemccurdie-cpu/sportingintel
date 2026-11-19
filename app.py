import os, base64, sqlite3, json, csv, io, re, difflib
from datetime import datetime, timezone
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Header
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
SANCTIONS_PATH=os.getenv("SANCTIONS_DATA_PATH","uk_sanctions.csv")
SANCTIONS_META={"loaded":False,"count":0,"filename":None,"loaded_at":None,"error":None}
class CounterpartyIn(BaseModel):
    company_number: str
    record: dict[str, Any]

def db():
    parent=os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
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

@app.put("/api/counterparties/{company_number}")
async def update_counterparty(company_number: str, payload: CounterpartyIn):
    if payload.company_number != company_number:
        raise HTTPException(400,"Company number mismatch.")
    con=db()
    con.execute("INSERT OR REPLACE INTO counterparties(company_number,record_json,created_at) VALUES(?,?,?)",
      (company_number,json.dumps(payload.record),stamp()))
    con.commit(); con.close()
    return {"saved":True,"company_number":company_number}

def stamp():
    return datetime.now(timezone.utc).isoformat()


def parse_uk_sanctions_csv(raw: bytes):
    try:
        decoded=raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded=raw.decode("cp1252",errors="replace")
    # The official FCDO export starts with a report-date metadata line before its CSV header.
    lines=decoded.splitlines()
    if lines and lines[0].lstrip().startswith("Report Date:"):
        decoded="\n".join(lines[1:])
    reader=csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames or "Unique ID" not in reader.fieldnames:
        raise HTTPException(422,"This does not look like the official UK Sanctions List CSV: expected a 'Unique ID' column.")
    grouped={}
    for row in reader:
        uid=(row.get("Unique ID") or "").strip()
        if not uid: continue
        rec=grouped.setdefault(uid,{"unique_id":uid,"names":[],"raw":row})
        for i in range(1,7):
            value=(row.get(f"Name {i}") or "").strip()
            if value and value.lower() not in {"na","n/a","none"} and value not in rec["names"]:
                rec["names"].append(value)
    return decoded,list(grouped.values())

def load_sanctions_csv(raw: bytes, filename: str):
    decoded,rows=parse_uk_sanctions_csv(raw)
    if not rows:
        raise HTTPException(422,"No designation records with a Unique ID and name fields were found.")
    parent=os.path.dirname(SANCTIONS_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(SANCTIONS_PATH,"w",encoding="utf-8",newline="") as f:
        f.write(decoded)
    SANCTIONS_META.update({"loaded":True,"count":len(rows),"filename":filename,"loaded_at":stamp(),"error":None})
    return rows

def sanctions_rows():
    if not os.path.exists(SANCTIONS_PATH):
        return []
    with open(SANCTIONS_PATH,"rb") as f: raw=f.read()
    _,rows=parse_uk_sanctions_csv(raw)
    return rows

@app.post("/api/sanctions/upload")
async def upload_sanctions(file: UploadFile=File(...), x_sanctions_admin: str=Header(default="")):
    expected=os.getenv("SANCTIONS_ADMIN_TOKEN","")
    if not expected:
        raise HTTPException(503,"SANCTIONS_ADMIN_TOKEN is not configured. Set it in Railway Variables before importing a list.")
    if x_sanctions_admin != expected:
        raise HTTPException(403,"Admin token required.")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(415,"Please upload a CSV file.")
    raw=await file.read()
    if len(raw)>100*1024*1024: raise HTTPException(413,"CSV exceeds 100 MB.")
    rows=load_sanctions_csv(raw,file.filename)
    return {"loaded":True,"filename":file.filename,"designations":len(rows),"loaded_at":SANCTIONS_META["loaded_at"],"report_date":(raw.decode("utf-8-sig",errors="replace").splitlines()[0].replace("Report Date:","").strip() if raw.startswith(b"Report Date:") else None),"message":"UK sanctions dataset imported and grouped by Unique ID. Name similarity results require analyst review."}

@app.post("/api/sanctions/refresh")
async def refresh_sanctions():
    """Download the current official UK Sanctions List CSV from the FCDO static URL."""
    url="https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv"
    try:
        async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
            response=await client.get(url, headers={"User-Agent":"SportingIntelligence-SanctionsScreen/1.0"})
        if response.status_code != 200:
            raise HTTPException(502, f"Official FCDO download returned HTTP {response.status_code}.")
        raw=response.content
        if len(raw)<1000 or b"Unique ID" not in raw[:20000]:
            raise HTTPException(502,"The downloaded file did not match the expected UK Sanctions List CSV format.")
        rows=load_sanctions_csv(raw,"UK-Sanctions-List.csv")
        first=raw.decode("utf-8-sig",errors="replace").splitlines()[0] if raw else ""
        report_date=first.replace("Report Date:","").strip() if first.startswith("Report Date:") else None
        return {"loaded":True,"filename":"UK-Sanctions-List.csv","designations":len(rows),"loaded_at":SANCTIONS_META["loaded_at"],"report_date":report_date,"source":url,"message":"Downloaded current official FCDO UK Sanctions List and indexed by Unique ID."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502,f"Could not download the official UK Sanctions List: {exc}")

@app.get("/api/sanctions/status")
async def sanctions_status():
    rows=sanctions_rows()
    return {"loaded":bool(rows),"designations":len(rows),"source":"Uploaded official UK Sanctions List CSV","message":"Dataset available" if rows else "No sanctions CSV loaded. No screening has been performed."}

@app.get("/api/sanctions/check")
async def sanctions_check(q: str | None = None, name: str | None = None):
    subject=(q or name or "").strip()
    if len(subject) < 2:
        raise HTTPException(422,"Provide a name of at least two characters to screen.")
    rows=sanctions_rows()
    if not rows:
        raise HTTPException(503,"No UK Sanctions List CSV is loaded. Upload the current official FCDO CSV before screening.")
    q=re.sub(r"[^a-z0-9 ]+"," ",subject.lower()).strip()
    matches=[]
    for row in rows:
        for candidate in row["names"]:
            norm=re.sub(r"[^a-z0-9 ]+"," ",candidate.lower()).strip()
            if len(norm) < 4:
                continue
            ratio=difflib.SequenceMatcher(None,q,norm).ratio()
            q_tokens=set(q.split()); n_tokens=set(norm.split())
            token_score=len(q_tokens & n_tokens)/max(1,len(q_tokens | n_tokens))
            # Do not match a multi-word person to a common one-word alias such as
            # "Vladimir". Full-name fuzzy matching requires meaningful token overlap.
            contained=(len(q_tokens)==1 and len(n_tokens)==1 and min(len(q),len(norm))>=6 and (q in norm or norm in q))
            strong_full_match=(len(q_tokens)>=2 and len(n_tokens)>=2 and (ratio>=0.86 or token_score>=0.80))
            surname_alias=(len(q_tokens)>=2 and len(n_tokens)==1 and len(norm)>=7 and norm==q.split()[-1])
            if q==norm or contained or strong_full_match or surname_alias:
                matches.append({"matched_name":candidate,"similarity":round(max(ratio,token_score),4),"similarity_percent":round(max(ratio,token_score)*100,1),"record":row["raw"]})
    unique=[]; seen=set()
    for match in matches:
        key=(match["record"].get("Unique ID"),match["matched_name"].casefold())
        if key not in seen:
            seen.add(key); unique.append(match)
    matches=unique
    status="Potential matches" if matches else "No potential name matches in loaded dataset"
    message=("Potential name match(es) found. These are not confirmed matches; verify identifiers and aliases." if matches else "No potential name matches found in the loaded dataset. This is not a clean-screen conclusion; verify spelling, aliases and identifiers.")
    return {"query":subject,"status":status,"match_count":len(matches),"matches":matches[:20],"potential_matches":matches[:20],"refreshed_at":SANCTIONS_META.get("loaded_at"),"dataset_designations":len(rows),"source":"Uploaded UK Sanctions List CSV","message":message,"disclaimer":"Name similarity is a screening lead only, not confirmation of identity or a confirmed sanctions hit."}

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
    @app.get("/about.html")
async def about_page():
    return FileResponse("static/about.html")

app.mount("/", StaticFiles(directory="static", html=True), name="static")

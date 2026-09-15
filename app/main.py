from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from .database import get_conn, init_db
from .matcher import match_job

BASE = Path(__file__).resolve().parent.parent
app = FastAPI(title="AI Job Application Tracker + Smart Matcher")

class JobIn(BaseModel):
    company: str
    title: str
    location: str = ""
    work_model: str = ""
    posting_date: str = ""
    source: str = ""
    url: str = ""
    description: str
    status: str = "FOUND"
    notes: str = ""

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def home():
    return FileResponse(BASE / "static" / "index.html")

@app.get("/api/jobs")
def list_jobs():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()]
    conn.close()
    for row in rows:
        row["match"] = match_job(row)
    return rows

@app.post("/api/jobs")
def create_job(job: JobIn):
    match = match_job(job.model_dump())
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO jobs
        (company,title,location,work_model,posting_date,source,url,description,status,best_resume,notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (job.company, job.title, job.location, job.work_model, job.posting_date,
         job.source, job.url, job.description, job.status, match["best_resume"], job.notes)
    )
    conn.commit()
    job_id = cur.lastrowid
    conn.close()
    return {"id": job_id, "match": match}

@app.patch("/api/jobs/{job_id}/status")
def update_status(job_id: int, status: str):
    allowed = {"FOUND","SHORTLISTED","APPLIED","OA / TEST","INTERVIEW","OFFER","REJECTED","ACCEPTED"}
    if status not in allowed:
        raise HTTPException(400, "Invalid status")
    conn = get_conn()
    cur = conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "Job not found")
    return {"ok": True}

@app.get("/api/jobs/{job_id}/match")
def get_match(job_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Job not found")
    return match_job(dict(row))

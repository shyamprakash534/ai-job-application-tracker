import io
import re
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader
from docx import Document

from .matcher import extract_skills, match_job

BASE = Path(__file__).resolve().parent.parent
app = FastAPI(title="AI Job Matcher")

class SearchRequest(BaseModel):
    resume_text: str = ""
    skills: list[str] = []
    locations: list[str] = []
    work_modes: list[str] = []
    roles: list[str] = []


def extract_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_resume(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        return extract_docx(data)
    raise HTTPException(400, "Please upload a PDF or DOCX resume.")


@app.get("/")
def home():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/api/resume/parse")
async def parse_resume(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Resume must be 5 MB or smaller.")
    text = extract_resume(file.filename or "resume.pdf", data)
    if len(text.strip()) < 50:
        raise HTTPException(400, "Could not extract enough text from this resume.")
    return {"text": text, "skills": extract_skills(text)}


async def fetch_jobicy(client: httpx.AsyncClient, skills: list[str]):
    tag = skills[0] if skills else "software"
    try:
        r = await client.get("https://jobicy.com/api/v2/remote-jobs", params={"count": 100, "tag": tag}, timeout=15)
        r.raise_for_status()
        data = r.json()
        jobs = []
        for j in data.get("jobs", []):
            jobs.append({
                "id": f"jobicy-{j.get('id')}", "source": "Jobicy", "company": j.get("companyName", ""),
                "title": j.get("jobTitle", ""), "location": j.get("jobGeo", "Remote"),
                "work_model": "Remote", "posting_date": j.get("pubDate", ""),
                "url": j.get("url", ""), "description": re.sub(r"<[^>]+>", " ", j.get("jobDescription", "")),
                "remote": True, "salary": f"{j.get('salaryMin','')} - {j.get('salaryMax','')} {j.get('salaryCurrency','')}".strip(" -"),
            })
        return jobs
    except Exception:
        return []


async def fetch_hopin(client: httpx.AsyncClient):
    try:
        r = await client.get("https://api.hopinjobs.com/api/jobs", params={"is_unofficial": "true"}, timeout=15)
        r.raise_for_status()
        jobs = []
        for j in r.json().get("jobs", []):
            jobs.append({
                "id": f"hopin-{j.get('id')}", "source": "Hopin", "company": j.get("company", ""),
                "title": j.get("title", ""), "location": j.get("location", ""),
                "work_model": j.get("work_type", ""), "posting_date": j.get("posted_at", ""),
                "url": f"https://www.hopinjobs.com/jobs/{j.get('id')}", "description": j.get("description", ""),
                "remote": "remote" in j.get("work_type", "").lower() or "remote" in j.get("location", "").lower(),
                "salary": j.get("ctc_amount", ""),
            })
        return jobs
    except Exception:
        return []


@app.post("/api/match-jobs")
async def match_jobs(req: SearchRequest):
    if not req.resume_text.strip() and not req.skills:
        raise HTTPException(400, "Upload a resume or add at least one skill.")
    async with httpx.AsyncClient(headers={"User-Agent": "AI-Job-Matcher/1.0"}) as client:
        remote_jobs, india_jobs = await __import__("asyncio").gather(fetch_jobicy(client, req.skills), fetch_hopin(client))
    jobs = {j["id"]: j for j in remote_jobs + india_jobs}.values()
    results = []
    for job in jobs:
        if req.roles and not any(r.lower() in job["title"].lower() for r in req.roles):
            continue
        result = match_job(job, req.resume_text, req.skills, req.locations)
        if req.work_modes and job["work_model"] and not any(m.lower() in job["work_model"].lower() for m in req.work_modes):
            continue
        job["match"] = result
        results.append(job)
    results.sort(key=lambda x: (x["match"]["score"], x.get("posting_date", "")), reverse=True)
    return {"count": len(results), "jobs": results[:100], "profile_skills": extract_skills(req.resume_text, req.skills)}

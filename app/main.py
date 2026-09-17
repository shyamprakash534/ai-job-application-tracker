import asyncio
import io
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from pypdf import PdfReader
from docx import Document

from .matcher import extract_skills, match_job

BASE = Path(__file__).resolve().parent.parent
APP_VERSION = "2026.09.17.3"
app = FastAPI(title="AI Job Matcher", version=APP_VERSION)


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
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        return extract_docx(data)
    raise HTTPException(400, "Please upload a PDF or DOCX resume.")


def hopin_slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", (value or "").lower())
    return value.strip("-")


def hopin_job_url(job: dict) -> str:
    jid = str(job.get("id") or "").strip()
    if not jid:
        return ""
    title = hopin_slug(job.get("title", ""))
    company = hopin_slug(job.get("company", ""))
    parts = [p for p in (title, company, jid) if p]
    return "https://hopinjobs.com/jobs/" + "-".join(parts)


def extract_application_url(text: str) -> str:
    """Find a genuine employer/ATS application or careers URL in listing text."""
    urls = re.findall(r"https?://[^\s<>\"']+", text or "")
    cleaned = [u.rstrip(".,);]}") for u in urls]
    blocked_hosts = {
        "wa.me", "whatsapp.com", "www.whatsapp.com",
        "linkedin.com", "www.linkedin.com", "x.com", "twitter.com",
        "hopinjobs.com", "www.hopinjobs.com",
    }
    candidates = []
    for url in cleaned:
        try:
            host = (urlparse(url).hostname or "").lower()
        except Exception:
            continue
        if not host or host in blocked_hosts or host.endswith(".linkedin.com") or host.endswith(".whatsapp.com") or host.endswith(".hopinjobs.com"):
            continue
        candidates.append(url)
    for url in candidates:
        low = url.lower()
        if any(token in low for token in (
            "apply", "career", "careers", "jobs", "job", "workday",
            "greenhouse", "lever", "smartrecruiters", "myworkdayjobs",
            "ashbyhq", "successfactors", "icims", "taleo",
        )):
            return url
    return candidates[0] if candidates else ""


def extract_application_url_from_job(job: dict) -> str:
    """Search all Hopin job fields for an employer/ATS URL, not just description."""
    preferred_keys = (
        "application_url", "apply_url", "applyUrl", "applicationUrl",
        "careers_url", "careersUrl", "career_url", "careerUrl",
        "company_url", "companyUrl", "company_website", "companyWebsite",
        "website", "job_url", "jobUrl", "redirect_url", "redirectUrl",
    )
    values = []
    for key in preferred_keys:
        value = job.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value)
    for key, value in job.items():
        if key in preferred_keys or key in {"description", "id", "title", "company"}:
            continue
        if isinstance(value, str) and "http" in value.lower():
            values.append(value)
    values.append(job.get("description", ""))
    return extract_application_url("\n".join(values))


def source_job_url(job: dict) -> str:
    """Use employer/ATS application URL only; never route Hopin listings to Hopin."""
    application_url = str(job.get("application_url") or "").strip()
    if application_url:
        return application_url
    if job.get("source") == "Hopin":
        return ""
    return str(job.get("url") or "")


@app.get("/")
def home():
    response = FileResponse(BASE / "static" / "index.html", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "X-JobMatch-Version": APP_VERSION,
    })
    return response


@app.get("/health")
def health():
    return Response(
        content='{"status":"ok","app":"AI Job Matcher","version":"%s"}' % APP_VERSION,
        media_type="application/json",
        headers={"Cache-Control": "no-store", "X-JobMatch-Version": APP_VERSION},
    )


@app.post("/api/resume/parse")
async def parse_resume(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Resume must be 5 MB or smaller.")
    try:
        text = extract_resume(file.filename or "resume.pdf", data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Could not read this resume: {exc}") from exc
    if len(text.strip()) < 50:
        raise HTTPException(400, "Could not extract enough text from this resume.")
    return {"text": text, "skills": extract_skills(text)}


async def fetch_jobicy(client: httpx.AsyncClient, skills: list[str]):
    try:
        tags = [s for s in skills if s.strip()][:4] or ["software"]
        batches = await asyncio.gather(*[
            client.get("https://jobicy.com/api/v2/remote-jobs", params={"count": 200, "tag": tag}, timeout=15)
            for tag in tags
        ], return_exceptions=True)
        jobs_by_id = {}
        for response in batches:
            if isinstance(response, Exception) or response.status_code != 200:
                continue
            try:
                data = response.json()
            except Exception:
                continue
            for j in data.get("jobs", []):
                jid = j.get("id")
                if jid is None:
                    continue
                description = re.sub(r"<[^>]+>", " ", j.get("jobDescription", ""))
                source_url = j.get("url", "")
                application_url = extract_application_url(description)
                jobs_by_id[f"jobicy-{jid}"] = {
                    "id": f"jobicy-{jid}", "source": "Jobicy", "company": j.get("companyName", ""),
                    "title": j.get("jobTitle", ""), "location": j.get("jobGeo", "Remote"), "work_model": "Remote",
                    "posting_date": j.get("pubDate", ""), "url": source_url, "source_url": source_url,
                    "application_url": application_url,
                    "description": description, "remote": True,
                    "salary": f"{j.get('salaryMin','')} - {j.get('salaryMax','')} {j.get('salaryCurrency','')}".strip(" -"),
                }
        return list(jobs_by_id.values())
    except Exception:
        return []


async def fetch_hopin(client: httpx.AsyncClient):
    try:
        r = await client.get("https://api.hopinjobs.com/api/jobs", params={"is_unofficial": "true"}, timeout=15)
        r.raise_for_status()
        jobs = []
        for j in r.json().get("jobs", []):
            jid = j.get("id")
            if not jid:
                continue
            description = j.get("description", "")
            application_url = extract_application_url_from_job(j)
            # IMPORTANT: never expose the Hopin page as the clickable job URL.
            source_url = application_url
            jobs.append({
                "id": f"hopin-{jid}", "source": "Hopin", "company": j.get("company", ""),
                "title": j.get("title", ""), "location": j.get("location", ""), "work_model": j.get("work_type", ""),
                "posting_date": j.get("posted_at", ""), "url": application_url, "source_url": source_url,
                "application_url": application_url, "source_job_id": str(jid),
                "description": description,
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
        remote_jobs, india_jobs = await asyncio.gather(fetch_jobicy(client, req.skills), fetch_hopin(client))

    jobs = {j["id"]: j for j in remote_jobs + india_jobs}.values()
    results = []
    requested_modes = {m.strip().lower() for m in req.work_modes if m.strip()}

    for job in jobs:
        title = job.get("title", "")
        if req.roles and not any(r.strip().lower() in title.lower() for r in req.roles if r.strip()):
            continue
        if requested_modes:
            job_mode = (job.get("work_model") or "").lower()
            if job_mode and not any(mode in job_mode for mode in requested_modes):
                continue
        result = match_job(job, req.resume_text, req.skills, req.locations)
        job["match"] = result
        job["source_url"] = source_job_url(job)
        results.append(job)

    results.sort(key=lambda x: (x["match"]["score"], x.get("posting_date", "")), reverse=True)
    return {
        "count": len(results), "jobs": results[:100],
        "profile_skills": extract_skills(req.resume_text, req.skills),
        "source_counts": {"Jobicy": sum(1 for j in results if j.get("source") == "Jobicy"), "Hopin": sum(1 for j in results if j.get("source") == "Hopin")},
        "version": APP_VERSION,
    }

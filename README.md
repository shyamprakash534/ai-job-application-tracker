# JobMatch AI

Public job-matching website: upload a resume, add skills, choose preferred locations, and get ranked jobs that match the profile.

## Live Demo

**https://ai-job-application-tracker-o9vp.onrender.com**

## User flow
1. Upload PDF/DOCX resume.
2. Add extra skills.
3. Enter preferred locations such as Hyderabad, Bengaluru, Chennai or Remote.
4. Optionally choose job roles and work models.
5. Click **Find Matching Jobs**.
6. The backend discovers jobs and ranks them by resume relevance, skills, location and eligibility.
7. Click **View & Apply** to open the job source's official listing page first, then continue through that listing's Apply / employer application flow.

## Current job sources
- **Jobicy** public remote-jobs API for remote listings. The integration keeps the original Jobicy URL/source attribution.
- **Hopin Jobs** public read-only API for India job listings.

These sources are intentionally used server-side so the browser never needs third-party API credentials.

## Application links

JobMatch AI does not guess or construct arbitrary application URLs. **View & Apply** opens the canonical job listing page supplied or reconstructed for the configured source.

- **Jobicy:** opens the canonical Jobicy listing, where the user can continue to the employer website/application.
- **Hopin Jobs:** opens the public Hopin job listing, where the available application flow or employer link is presented by the listing.

This source-first approach helps avoid broken or stale direct-application URLs.

## Matching model
- Resume relevance: 30%
- Skills: 35%
- Preferred location: 20%
- Experience eligibility: 10%
- Role/title relevance: 5%

If a user explicitly chooses locations and a job does not match them, the score is capped so an unrelated location cannot outrank a preferred location.

## Stack
- Python
- FastAPI
- httpx
- pypdf + python-docx for resume extraction
- Vanilla HTML/CSS/JavaScript

## Run locally
```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Deployment
Render build command:
```text
pip install -r requirements.txt
```

Render start command:
```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Important
Job availability depends on the connected public job sources. The application does not claim to contain every job on the internet. It ranks the listings returned by its configured sources.

# AI Job Application Tracker + Smart Matcher

A FastAPI + SQLite MVP for tracking job applications and matching each job independently against four role-specific resume profiles.

## Four resume profiles
1. Data Analyst
2. AWS Cloud / Data Engineer
3. Backend / Platform Generalist
4. AI/ML / GenAI

## Stack
- Python
- FastAPI
- SQLite
- Vanilla HTML/CSS/JavaScript

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Features
- Job application tracking and status workflow
- Search and status/resume filters
- Four independent resume match scores
- Best-resume recommendation
- Skill, title, project and experience signals
- Experience hard-stop flags
- Application URL support
- Responsive JobOS dashboard

## Matching model
The initial deterministic matcher scores:
- skills: 35%
- title/role: 20%
- experience eligibility: 15%
- location/work model: 10%
- project relevance: 10%
- education: 5%
- other requirements: 5%

Hard-stop requirements are reported separately so a high keyword score cannot hide a genuine eligibility problem.

## Deployment
Designed for deployment as a Python web service on Render using:

```text
Build: pip install -r requirements.txt
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

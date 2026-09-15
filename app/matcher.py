import re

PROFILES = {
    "Data Analyst": {
        "titles": ["data analyst", "bi analyst", "business analyst", "reporting analyst", "data operations"],
        "skills": ["python", "sql", "pandas", "numpy", "tableau", "power bi", "matplotlib", "mysql", "postgresql", "sqlite"],
        "projects": ["churn", "customer", "dashboard", "eda", "data analysis", "etl"]
    },
    "AWS Cloud / Data Engineer": {
        "titles": ["data engineer", "cloud engineer", "aws", "cloud", "devops", "analytics engineer"],
        "skills": ["aws", "s3", "ec2", "lambda", "rds", "iam", "cloudwatch", "glue", "athena", "sql", "docker", "terraform", "postgresql", "redis", "clickhouse"],
        "projects": ["etl", "aws", "cloud", "pipeline", "nanolink", "clickhouse"]
    },
    "Backend / Platform Generalist": {
        "titles": ["software engineer", "software developer", "python developer", "backend developer", "backend engineer", "full stack developer", "platform engineer"],
        "skills": ["python", "sql", "flask", "fastapi", "rest api", "docker", "git", "github", "postgresql", "redis", "clickhouse", "go", "javascript"],
        "projects": ["nanolink", "backend", "api", "distributed", "postgresql", "redis"]
    },
    "AI/ML / GenAI": {
        "titles": ["machine learning engineer", "ml engineer", "ai engineer", "ai/ml", "genai", "ai developer", "python developer"],
        "skills": ["python", "scikit-learn", "random forest", "gradient boosting", "decision trees", "shap", "rag", "langgraph", "chromadb", "ollama", "fastapi", "flask", "docker"],
        "projects": ["drug", "churn", "rag", "codeforge", "machine learning", "genai"]
    }
}

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())

def contains(text, term):
    return term in text

def match_job(job: dict):
    text = normalize(f"{job.get('title','')} {job.get('description','')}")
    title = normalize(job.get("title", ""))
    results = {}
    for profile, cfg in PROFILES.items():
        skill_hits = [s for s in cfg["skills"] if contains(text, s)]
        title_hits = [t for t in cfg["titles"] if contains(title, t)]
        project_hits = [p for p in cfg["projects"] if contains(text, p)]
        skill_score = min(100, round(len(skill_hits) / max(1, min(8, len(cfg["skills"]))) * 100))
        title_score = 100 if title_hits else (55 if any(x in title for x in ["analyst", "engineer", "developer"]) else 0)
        project_score = min(100, round(len(project_hits) / max(1, min(4, len(cfg["projects"]))) * 100))
        exp_match = 100
        hard_stops = []
        if re.search(r"(?:2|3|4|5|6|7|8|9|10)\+?\s*(?:years?|yrs?)", text):
            exp_match = 0
            hard_stops.append("Experience requirement may exceed fresher/0–1 year profile.")
        score = round(skill_score * .35 + title_score * .20 + exp_match * .15 + 70 * .10 + project_score * .10 + 70 * .05 + 70 * .05)
        results[profile] = {"score": score, "skill_hits": skill_hits, "title_hits": title_hits, "project_hits": project_hits, "hard_stops": hard_stops}
    best = max(results.items(), key=lambda x: x[1]["score"])
    return {"profiles": results, "best_resume": best[0], "best_score": best[1]["score"]}

import re

SKILL_ALIASES = {
    "python": ["python"], "sql": ["sql", "mysql", "postgresql", "postgres"], "aws": ["aws", "amazon web services"],
    "azure": ["azure"], "gcp": ["gcp", "google cloud"], "fastapi": ["fastapi"], "flask": ["flask"], "django": ["django"],
    "javascript": ["javascript", "js"], "typescript": ["typescript", "ts"], "react": ["react", "react.js"],
    "node.js": ["node.js", "nodejs"], "docker": ["docker"], "kubernetes": ["kubernetes", "k8s"], "git": ["git", "github"],
    "pandas": ["pandas"], "numpy": ["numpy"], "scikit-learn": ["scikit-learn", "sklearn"], "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning"], "tensorflow": ["tensorflow"], "pytorch": ["pytorch"], "power bi": ["power bi"],
    "tableau": ["tableau"], "mongodb": ["mongodb", "mongo"], "spark": ["spark", "pyspark"], "hadoop": ["hadoop"],
    "excel": ["excel", "microsoft excel"], "java": ["java"], "c++": ["c++"], "rest api": ["rest api", "restful api", "restful"],
    "llm": ["llm", "large language model"], "genai": ["genai", "generative ai"],
}
TITLE_KEYWORDS = ["software engineer", "software developer", "python developer", "backend developer", "backend engineer", "full stack developer", "data analyst", "data engineer", "machine learning engineer", "ml engineer", "ai engineer", "ai developer", "cloud engineer", "devops engineer", "business analyst", "qa engineer", "test engineer"]

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def extract_skills(text: str, extra_skills=None) -> list[str]:
    text = normalize(text); found = set()
    for canonical, aliases in SKILL_ALIASES.items():
        if any(re.search(r"(?<!\w)" + re.escape(a.strip()) + r"(?!\w)", text) for a in aliases): found.add(canonical)
    for skill in extra_skills or []:
        if normalize(skill): found.add(normalize(skill))
    return sorted(found)

def location_score(job_location: str, preferred_locations: list[str], remote=False):
    if not preferred_locations: return 70, False
    text = normalize(job_location)
    for loc in preferred_locations:
        loc = normalize(loc)
        if loc and (loc in text or text in loc): return 100, True
    if remote and any(x in normalize(" ".join(preferred_locations)) for x in ["remote", "anywhere", "worldwide"]): return 100, True
    return 0, False

def experience_score(text: str):
    years = [int(x) for x in re.findall(r"\b(\d+)\+?\s*(?:years?|yrs?)", text.lower())]
    if years and min(years) >= 2: return 0, [f"Requires {min(years)}+ years of experience."]
    if any(x in text.lower() for x in ["entry level", "entry-level", "fresher", "graduate", "0-1 year", "0–1 year", "junior"]): return 100, []
    return 70, []

def match_job(job: dict, resume_text: str, user_skills: list[str], preferred_locations: list[str]):
    combined = normalize(f"{job.get('title', '')} {job.get('description', '')}"); resume = normalize(resume_text)
    profile_skills = extract_skills(resume, user_skills); job_skills = extract_skills(combined)
    matched = sorted(set(profile_skills) & set(job_skills)); missing = sorted(set(job_skills) - set(profile_skills))
    skill_score = round(len(matched) / max(1, len(job_skills)) * 100); title = normalize(job.get("title", ""))
    title_score = 100 if any(k in title for k in TITLE_KEYWORDS) and any(k in resume for k in title.split()) else 60 if any(k in title for k in TITLE_KEYWORDS) else 35
    resume_words = set(re.findall(r"[a-z][a-z+#.-]{2,}", resume)); job_words = set(re.findall(r"[a-z][a-z+#.-]{2,}", combined))
    resume_score = min(100, 45 + len(resume_words & job_words) * 3); exp_score, hard_stops = experience_score(combined)
    loc_score, loc_match = location_score(job.get("location", ""), preferred_locations, bool(job.get("remote")))
    score = round(resume_score * .30 + skill_score * .35 + loc_score * .20 + exp_score * .10 + title_score * .05)
    if preferred_locations and not loc_match: score = min(score, 59)
    return {"score": score, "matched_skills": matched, "missing_skills": missing[:12], "location_match": loc_match, "location_score": loc_score, "experience_score": exp_score, "hard_stops": hard_stops}

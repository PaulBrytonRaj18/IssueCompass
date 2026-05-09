from typing import Dict, List, Any, Optional
import hashlib
import numpy as np
from app.services.github_service import fetch_user_repos, fetch_repo_languages


def _stable_hash(text: str, modulus: int) -> int:
    """Deterministic stable hash for consistent vector positions."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16) % modulus


# Skill taxonomy — maps raw language/topic to categories
SKILL_CATEGORIES = {
    "frontend": [
        "javascript", "typescript", "react", "vue", "angular", "svelte",
        "nextjs", "nuxtjs", "html", "css", "tailwind", "sass", "webpack",
        "vite", "redux", "graphql", "frontend",
    ],
    "backend": [
        "python", "fastapi", "django", "flask", "nodejs", "express",
        "java", "spring", "golang", "rust", "ruby", "rails", "php",
        "laravel", "dotnet", "csharp", "kotlin", "scala", "backend",
        "rest-api", "microservices",
    ],
    "database": [
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "sqlite", "database", "sql", "nosql", "cassandra", "firebase",
        "supabase", "prisma", "sqlalchemy", "orm",
    ],
    "devops": [
        "docker", "kubernetes", "terraform", "ansible", "jenkins",
        "github-actions", "ci-cd", "aws", "gcp", "azure", "linux",
        "nginx", "devops", "infrastructure", "cloud",
    ],
    "ai_ml": [
        "python", "pytorch", "tensorflow", "keras", "scikit-learn",
        "machine-learning", "deep-learning", "nlp", "computer-vision",
        "jupyter", "pandas", "numpy", "transformers", "llm", "ai",
        "data-science",
    ],
    "mobile": [
        "swift", "kotlin", "react-native", "flutter", "dart", "android",
        "ios", "mobile",
    ],
    "systems": [
        "rust", "c", "cpp", "c++", "assembly", "embedded", "firmware",
        "systems", "low-level",
    ],
}

SKILL_VECTOR_DIMS = 128


def build_skill_fingerprint(
    repos: List[Dict[str, Any]],
    languages_map: Optional[Dict[str, Dict[str, int]]] = None,
) -> Dict[str, Any]:
    """
    Analyze repos to produce a structured skill fingerprint.
    
    Args:
        repos: List of GitHub repo objects
        languages_map: Optional map of repo_full_name -> {language: bytes}
    
    Returns:
        Structured skill fingerprint dict
    """
    lang_totals: Dict[str, int] = {}
    topic_counts: Dict[str, int] = {}
    total_stars = 0

    for repo in repos:
        if repo.get("fork"):
            continue  # skip forks for skill analysis
        
        # Languages
        lang = repo.get("language")
        if lang:
            lang_lower = lang.lower()
            lang_totals[lang_lower] = lang_totals.get(lang_lower, 0) + 1

        # Topics/tags
        for topic in repo.get("topics", []) or []:
            topic_lower = topic.lower()
            topic_counts[topic_lower] = topic_counts.get(topic_lower, 0) + 1

        total_stars += repo.get("stargazers_count", 0)

    # Add language data from languages_map if provided
    if languages_map:
        for repo_langs in languages_map.values():
            for lang, bytes_count in repo_langs.items():
                lang_lower = lang.lower()
                # Weight by bytes written (more meaningful than repo count)
                lang_totals[lang_lower] = lang_totals.get(lang_lower, 0) + max(1, bytes_count // 10000)

    # Normalize language scores to 0-1
    total_lang_weight = sum(lang_totals.values()) or 1
    languages_normalized = {
        lang: round(count / total_lang_weight, 3)
        for lang, count in sorted(lang_totals.items(), key=lambda x: -x[1])
    }

    # Categorize skills
    categories: Dict[str, List[str]] = {}
    all_skills = set(lang_totals.keys()) | set(topic_counts.keys())

    for category, keywords in SKILL_CATEGORIES.items():
        matched = [s for s in all_skills if any(kw in s for kw in keywords)]
        if matched:
            categories[category] = list(set(matched))[:10]

    # Top skills (top 10 by frequency)
    all_skill_scores = {**lang_totals, **topic_counts}
    top_skills = [
        skill for skill, _ in sorted(all_skill_scores.items(), key=lambda x: -x[1])
    ][:10]

    # Experience level heuristic
    total_repos = len([r for r in repos if not r.get("fork")])
    if total_repos < 5:
        experience_level = "beginner"
    elif total_repos < 20:
        experience_level = "intermediate"
    else:
        experience_level = "advanced"

    return {
        "languages": languages_normalized,
        "topics": list(topic_counts.keys())[:20],
        "categories": categories,
        "experience_level": experience_level,
        "top_skills": top_skills,
        "total_repos": total_repos,
        "total_stars_received": total_stars,
    }


def skill_fingerprint_to_vector(fingerprint: Dict[str, Any]) -> List[float]:
    """
    Convert a skill fingerprint dict to a fixed-size 128-dim vector
    for pgvector similarity search.
    """
    # We use a deterministic hashing approach to map skills to vector positions
    vector = np.zeros(SKILL_VECTOR_DIMS, dtype=np.float32)

    languages = fingerprint.get("languages", {})
    topics = fingerprint.get("topics", [])
    categories = fingerprint.get("categories", {})

    # Fill first 64 dims with language scores
    for lang, score in languages.items():
        idx = _stable_hash(lang, 64)
        vector[idx] = max(vector[idx], float(score))

    # Fill dims 64-96 with topic presence
    for topic in topics:
        idx = 64 + _stable_hash(topic, 32)
        vector[idx] = min(vector[idx] + 0.1, 1.0)

    # Fill dims 96-128 with category presence
    category_list = list(SKILL_CATEGORIES.keys())
    for i, cat in enumerate(category_list):
        if cat in categories:
            idx = 96 + (i % 32)
            vector[idx] = min(len(categories[cat]) / 5.0, 1.0)

    # Normalize the vector
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.tolist()


def issue_text_to_vector(title: str, body: str, labels: List[str]) -> List[float]:
    """
    Convert issue text to a skill vector for matching.
    Uses keyword detection against our skill taxonomy.
    """
    combined_text = f"{title} {body} {' '.join(labels)}".lower()
    vector = np.zeros(SKILL_VECTOR_DIMS, dtype=np.float32)

    # Detect languages in text
    all_langs = [
        "python", "javascript", "typescript", "java", "go", "rust",
        "ruby", "php", "swift", "kotlin", "c++", "c#", "scala", "r",
        "react", "vue", "angular", "django", "flask", "fastapi",
        "express", "spring", "rails", "laravel", "nodejs",
    ]
    for lang in all_langs:
        if lang in combined_text:
            idx = _stable_hash(lang, 64)
            vector[idx] = max(vector[idx], 0.8)

    # Detect topics
    for topic_kw in ["frontend", "backend", "api", "database", "ui", "ux",
                     "test", "bug", "feature", "documentation", "performance",
                     "security", "docker", "kubernetes", "ci", "deployment"]:
        if topic_kw in combined_text:
            idx = 64 + _stable_hash(topic_kw, 32)
            vector[idx] = min(vector[idx] + 0.15, 1.0)

    # Detect categories
    category_list = list(SKILL_CATEGORIES.keys())
    for i, (cat, keywords) in enumerate(SKILL_CATEGORIES.items()):
        matches = sum(1 for kw in keywords if kw in combined_text)
        if matches > 0:
            idx = 96 + (i % 32)
            vector[idx] = min(matches / 3.0, 1.0)

    # Normalize
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.tolist()


def extract_required_skills(title: str, body: str, labels: List[str]) -> Dict[str, Any]:
    """Extract required skills from issue title, body, and labels."""
    combined = f"{title} {body} {' '.join(labels)}".lower()
    detected: Dict[str, List[str]] = {}

    for category, keywords in SKILL_CATEGORIES.items():
        found = [kw for kw in keywords if kw in combined]
        if found:
            detected[category] = found[:5]

    # Estimate complexity
    complexity = 0.5
    if any(w in combined for w in ["beginner", "easy", "simple", "starter", "first"]):
        complexity = 0.2
    elif any(w in combined for w in ["complex", "advanced", "difficult", "expert"]):
        complexity = 0.8

    return {
        "categories": detected,
        "complexity": complexity,
        "labels": labels,
    }


async def build_user_skills(github_username: str) -> Dict[str, Any]:
    """Full pipeline: fetch GitHub data → build skill fingerprint."""
    repos = await fetch_user_repos(github_username)
    fingerprint = build_skill_fingerprint(repos)
    return fingerprint

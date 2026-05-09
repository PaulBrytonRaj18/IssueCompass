from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.models import Issue, Repository, User
from app.services.skill_service import SKILL_CATEGORIES


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def explain_match(
    user_skills: Dict[str, Any],
    issue_skills: Dict[str, Any],
    match_score: float,
) -> tuple[List[str], str]:
    """
    Generate human-readable match explanation.
    Returns (matching_skills_list, why_matched_sentence)
    """
    user_langs = set(user_skills.get("languages", {}).keys())
    user_topics = set(user_skills.get("topics", []))
    user_top = set(user_skills.get("top_skills", []))

    issue_cats = issue_skills.get("categories", {})
    issue_labels = issue_skills.get("labels", [])

    # Find overlapping skills
    matching = set()
    for cat_skills in issue_cats.values():
        for skill in cat_skills:
            if skill in user_langs or skill in user_topics or skill in user_top:
                matching.add(skill)

    matching_list = list(matching)[:5]

    # Build explanation sentence
    if match_score > 0.8:
        strength = "Strong match"
    elif match_score > 0.5:
        strength = "Good match"
    else:
        strength = "Partial match"

    if matching_list:
        why = f"{strength} — your skills in {', '.join(matching_list[:3])} align with this issue."
    else:
        label_str = ", ".join(issue_labels[:2]) if issue_labels else "general"
        why = f"{strength} — this {label_str} issue fits your experience level."

    return matching_list, why


async def get_matched_issues(
    db: AsyncSession,
    user: User,
    limit: int = 30,
    offset: int = 0,
    language_filter: Optional[str] = None,
    label_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Find the best matching issues for a user using vector similarity.
    Falls back to keyword matching if user has no skill vector.
    """
    user_skill_json = user.skill_json or {}
    user_vector = user.skill_vector

    # Build query
    query = (
        select(Issue, Repository)
        .join(Repository, Issue.repository_id == Repository.id)
        .where(
            and_(
                Issue.state == "open",
                Issue.skill_vector.isnot(None),
            )
        )
    )

    if language_filter:
        query = query.where(Repository.primary_language.ilike(language_filter))

    if label_filter == "good_first":
        query = query.where(Issue.is_good_first_issue == True)
    elif label_filter == "help_wanted":
        query = query.where(Issue.is_help_wanted == True)

    pool_size = min(offset + limit * 3, 500)
    query = query.limit(pool_size)
    result = await db.execute(query)
    rows = result.fetchall()

    if not rows:
        return []

    # Score each issue
    scored = []
    for issue, repo in rows:
        if user_vector and issue.skill_vector:
            score = cosine_similarity(user_vector, issue.skill_vector)
        else:
            # Fallback: keyword overlap scoring
            score = _keyword_score(user_skill_json, issue)

        issue_skills = issue.required_skills or {}
        matching_skills, why = explain_match(user_skill_json, issue_skills, score)

        scored.append({
            "issue": issue,
            "repository": repo,
            "match_score": round(score, 4),
            "matching_skills": matching_skills,
            "why_matched": why,
        })

    # Sort by match score descending, then paginate
    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[offset:offset + limit]


def _keyword_score(user_skills: Dict[str, Any], issue: Issue) -> float:
    """Simple keyword overlap fallback when vectors aren't available."""
    user_langs = set(user_skills.get("languages", {}).keys())
    user_topics = set(user_skills.get("topics", []))
    all_user_skills = user_langs | user_topics

    issue_text = f"{issue.title or ''} {issue.body or ''}".lower()
    issue_labels = [l.lower() for l in (issue.labels or [])]

    matches = sum(
        1 for skill in all_user_skills
        if skill in issue_text or any(skill in lbl for lbl in issue_labels)
    )

    total = max(len(all_user_skills), 1)
    return min(matches / total, 1.0)

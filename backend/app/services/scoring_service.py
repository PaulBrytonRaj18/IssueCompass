import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.models import Issue, Repository
from app.services import ai_service

logger = logging.getLogger(__name__)

SCORE_WEIGHTS = {
    "skill_match": 0.50,
    "popularity": 0.15,
    "repo_activity": 0.10,
    "interest_match": 0.15,
    "freshness": 0.10,
}


def compute_repo_activity_score(repo: Repository) -> float:
    score = 0.5
    if repo.is_archived:
        return 0.0
    if repo.stars > 10000:
        score += 0.2
    elif repo.stars > 1000:
        score += 0.15
    elif repo.stars > 100:
        score += 0.1
    if repo.last_indexed:
        days_since = (datetime.now(timezone.utc) - repo.last_indexed).days
        if days_since < 7:
            score += 0.15
        elif days_since < 30:
            score += 0.1
    if repo.forks > 100:
        score += 0.1
    return min(score, 1.0)


def compute_freshness_score(issue: Issue) -> float:
    if not issue.created_at:
        return 0.3
    days_old = (datetime.now(timezone.utc) - issue.created_at).days
    if days_old < 7:
        return 1.0
    if days_old < 30:
        return 0.8
    if days_old < 90:
        return 0.5
    return 0.2


def compute_popularity_score(issue: Issue, repo: Repository) -> float:
    score = 0.0
    if issue.comments > 20:
        score += 0.3
    elif issue.comments > 5:
        score += 0.2
    elif issue.comments > 0:
        score += 0.1
    if repo.stars > 10000:
        score += 0.4
    elif repo.stars > 1000:
        score += 0.3
    elif repo.stars > 100:
        score += 0.2
    elif repo.stars > 10:
        score += 0.1
    if repo.forks > 1000:
        score += 0.2
    elif repo.forks > 100:
        score += 0.1
    return min(score, 1.0)


def compute_interest_match(
    user_skills: Dict[str, Any],
    issue_skills: Dict[str, Any],
) -> float:
    user_langs = set(user_skills.get("languages", {}).keys())
    user_topics = set(user_skills.get("topics", []))
    user_cats = set(user_skills.get("categories", {}).keys())
    user_top = set(user_skills.get("top_skills", []))

    issue_cats = set(issue_skills.get("categories", {}).keys())
    issue_labels = set(issue_skills.get("labels", []))

    if not user_langs and not user_topics:
        return 0.3

    combined_user = user_langs | user_topics | user_cats | user_top
    combined_issue = issue_cats | issue_labels

    if not combined_issue:
        return 0.3

    matches = len(combined_user & combined_issue)
    total = max(len(combined_user), 1)
    return min(matches / total, 1.0)


def compute_final_score(
    skill_similarity: float,
    repo_activity: float,
    freshness: float,
    interest_match: float,
    popularity: float,
) -> float:
    return (
        SCORE_WEIGHTS["skill_match"] * skill_similarity
        + SCORE_WEIGHTS["repo_activity"] * repo_activity
        + SCORE_WEIGHTS["freshness"] * freshness
        + SCORE_WEIGHTS["interest_match"] * interest_match
        + SCORE_WEIGHTS["popularity"] * popularity
    )


async def generate_ai_explanation(
    user_skills: Dict[str, Any],
    issue_skills: Dict[str, Any],
    match_score: float,
) -> Optional[str]:
    """Try to generate an AI-powered explanation, returns None if unavailable."""
    if not ai_service.AI_ENABLED:
        return None
    try:
        return await ai_service.generate_match_explanation(
            user_skills, issue_skills, match_score
        )
    except Exception as e:
        logger.debug("AI explanation failed: %s", e)
        return None


def explain_score(
    skill_similarity: float,
    repo_activity: float,
    freshness: float,
    interest_match: float,
    popularity: float,
    matching_skills: list[str],
) -> str:
    parts: list[str] = []

    final = compute_final_score(
        skill_similarity=skill_similarity,
        repo_activity=repo_activity,
        freshness=freshness,
        interest_match=interest_match,
        popularity=popularity,
    )

    if final > 0.8:
        parts.append("Strong match")
    elif final > 0.5:
        parts.append("Good match")
    else:
        parts.append("Partial match")

    score_pct = round(final * 100)
    parts.append(f"({score_pct}%)")

    if matching_skills:
        skill_str = ", ".join(matching_skills[:3])
        parts.append(f"— your {skill_str} skills align")

    repo_desc: list[str] = []
    if popularity > 0.7:
        repo_desc.append("highly popular repo")
    elif popularity > 0.4:
        repo_desc.append("popular repo")

    if repo_activity > 0.7:
        repo_desc.append("very active")
    elif repo_activity > 0.4:
        repo_desc.append("active")

    if freshness > 0.7:
        repo_desc.append("recently updated")

    if repo_desc:
        parts.append(f"({', '.join(repo_desc)})")

    return " ".join(parts)


def safe_explain_score(
    skill_similarity: float | None,
    repo_activity: float | None,
    freshness: float | None,
    interest_match: float | None,
    popularity: float | None,
    matching_skills: list[str] | None,
    fallback_score: float = 0.0,
    issue_id: object = None,
) -> str:
    """
    Wrapper around explain_score that catches errors and returns a fallback
    explanation string on failure. Never raises.
    """
    try:
        return explain_score(
            skill_similarity=skill_similarity or 0.0,
            repo_activity=repo_activity or 0.0,
            freshness=freshness or 0.0,
            interest_match=interest_match or 0.0,
            popularity=popularity or 0.0,
            matching_skills=matching_skills or [],
        )
    except Exception as exc:
        logger.warning(
            "explain_score failed for issue_id=%s: %s",
            issue_id, exc,
        )
        score_pct = round(max(0.0, min(1.0, fallback_score)) * 100)
        return f"Matched ({score_pct}%)"


# ---------------------------------------------------------------------------
# Live-issue proxy scorer
# Produces a 0–1 composite for a raw GitHub API issue dict.
# Called BEFORE the issue is embedded or persisted.
# ---------------------------------------------------------------------------

def score_live_issue(
    user_skills: dict,
    raw_issue: dict,
    raw_repo: dict,
) -> float:
    """
    Compute a blended 0-1 score for a live GitHub issue that has not yet been
    embedded or stored in the database.
    """
    # Skip pull requests (GitHub search returns PRs in issue search)
    if raw_issue.get("pull_request"):
        return 0.0

    user_languages = {k.lower() for k in user_skills.get("languages", {}).keys()}
    user_topics = {t.lower() for t in user_skills.get("topics", [])}
    user_top_skills = {s.lower() for s in user_skills.get("top_skills", [])}

    # ── 1. Language match (weight 0.40)
    repo_language = (raw_repo.get("language") or "").lower()
    repo_topics = {t.lower() for t in (raw_repo.get("topics") or [])}

    lang_score = 0.0
    if repo_language and repo_language in user_languages:
        lang_pct = user_skills.get("languages", {}).get(repo_language, 0)
        lang_score = min(1.0, 0.5 + lang_pct * 0.5)
    elif repo_language:
        lang_score = 0.0

    # ── 2. Topic / interest match (weight 0.20)
    topic_overlap = len(user_topics & repo_topics)
    topic_score = min(1.0, topic_overlap * 0.35)

    # ── 3. Label match (weight 0.15)
    label_names = {lbl["name"].lower() for lbl in raw_issue.get("labels", [])}
    label_score = 0.0
    if "good first issue" in label_names:
        label_score += 0.6
    if "help wanted" in label_names:
        label_score += 0.3
    if "bug" in label_names:
        label_score += 0.1
    label_score = min(1.0, label_score)

    # ── 4. Freshness (weight 0.15)
    updated_str = raw_issue.get("updated_at") or raw_issue.get("created_at", "")
    freshness_score = 0.2
    if updated_str:
        try:
            updated_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - updated_dt).days
            if age_days <= 7:
                freshness_score = 1.0
            elif age_days <= 30:
                freshness_score = 0.8
            elif age_days <= 90:
                freshness_score = 0.5
            else:
                freshness_score = 0.2
        except (ValueError, TypeError):
            freshness_score = 0.2

    # ── 5. Repo popularity (weight 0.10)
    stars = raw_repo.get("stargazers_count") or raw_repo.get("stars", 0)
    forks = raw_repo.get("forks_count") or raw_repo.get("forks", 0)
    pop_score = 0.0
    if stars >= 10_000:
        pop_score += 0.4
    elif stars >= 1_000:
        pop_score += 0.25
    elif stars >= 100:
        pop_score += 0.1
    if forks >= 1_000:
        pop_score += 0.2
    elif forks >= 100:
        pop_score += 0.1
    comments = raw_issue.get("comments", 0)
    if comments >= 20:
        pop_score += 0.3
    elif comments >= 5:
        pop_score += 0.15
    pop_score = min(1.0, pop_score)

    # ── Composite (weights must sum to 1.0)
    composite = (
        lang_score    * 0.40 +
        topic_score   * 0.20 +
        label_score   * 0.15 +
        freshness_score * 0.15 +
        pop_score     * 0.10
    )
    return round(composite, 4)


def build_live_issue_explanation(
    user_skills: dict,
    raw_issue: dict,
    raw_repo: dict,
    score: float,
) -> str:
    """
    Rule-based explanation string for a live issue (no AI call).
    """
    lang = (raw_repo.get("language") or "unknown").lower()
    pct = int(score * 100)
    label_names = [lbl["name"] for lbl in raw_issue.get("labels", [])]
    label_str = ", ".join(label_names[:3]) if label_names else "no labels"
    stars = raw_repo.get("stargazers_count") or raw_repo.get("stars", 0)
    repo_name = raw_repo.get("full_name") or raw_repo.get("name", "")

    quality = "Excellent" if score >= 0.8 else "Good" if score >= 0.6 else "Partial"
    return (
        f"{quality} match ({pct}%) — {lang} repo '{repo_name}' "
        f"[{label_str}], {stars:,} stars (live result)"
    )

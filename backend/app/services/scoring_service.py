import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.models.models import Issue, Repository
from app.services import ai_service

logger = logging.getLogger(__name__)

# ── Composite score weights (must sum to 1.0) ─────────────────────
SCORE_WEIGHTS = {
    "skill_match": 0.50,
    "popularity": 0.15,
    "repo_activity": 0.10,
    "interest_match": 0.15,
    "freshness": 0.10,
}

# ── Repo activity: star thresholds ────────────────────────────────
STARS_VERY_HIGH = 10_000  # threshold for very popular repos
STARS_HIGH = 1_000        # threshold for popular repos
STARS_MEDIUM = 100        # threshold for moderately popular repos

# ── Repo activity: days since last index ──────────────────────────
DAYS_RECENT = 7      # indexed within a week
DAYS_MONTH = 30      # indexed within a month

# ── Repo activity: fork threshold ─────────────────────────────────
FORKS_MODERATE = 100  # indicates moderate community engagement

# ── Freshness: day ranges ─────────────────────────────────────────
FRESH_DAYS = 7     # issue created within a week
MODERATE_DAYS = 30 # issue created within a month
STALE_DAYS = 90    # issue created within 3 months

# ── Popularity: comment thresholds ────────────────────────────────
COMMENTS_HIGH = 20   # many comments (high engagement)
COMMENTS_MODERATE = 5  # some discussion
COMMENTS_LOW = 0        # no comments (baseline)

# ── Popularity: fork thresholds ───────────────────────────────────
FORKS_HIGH = 1_000    # many forks (widespread interest)
FORKS_MODERATE_POP = 100  # moderate forks

# ── Popularity: star thresholds ───────────────────────────────────
STARS_TOP = 10_000   # top-tier popularity
STARS_ACTIVE = 1_000 # active popularity
STARS_KNOWN = 100    # known repo
STARS_MINIMAL = 10   # minimal popularity

# ── Live issue scorer: label boost values ──────────────────────────
LABEL_BOOST_GFI = 0.6  # "good first issue" increases match score
LABEL_BOOST_HELP = 0.3 # "help wanted" increases match score
LABEL_BOOST_BUG = 0.1  # "bug" label contributes slightly

# ── Live issue scorer: freshness defaults ─────────────────────────
FRESHNESS_DEFAULT = 0.2   # fallback when date is unparseable
FRESHNESS_RECENT = 1.0    # ≤ 7 days
FRESHNESS_MODERATE = 0.8  # ≤ 30 days
FRESHNESS_STALE = 0.5     # ≤ 90 days

# ── Explain-score quality thresholds ──────────────────────────────
QUALITY_EXCELLENT = 0.8  # "Strong match" threshold
QUALITY_GOOD = 0.5       # "Good match" threshold


def _days_since(dt: datetime) -> int:
    """Return whole days elapsed since ``dt``, accepting naive or aware datetimes."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days

# ── Explain-score descriptor thresholds ───────────────────────────
DESC_HIGH = 0.7   # "highly popular / very active / recently updated"
DESC_MEDIUM = 0.4 # "popular / active" floor


def compute_repo_activity_score(repo: Repository) -> float:
    score = 0.5
    if repo.is_archived:
        return 0.0
    if repo.stars > STARS_VERY_HIGH:
        score += 0.2
    elif repo.stars > STARS_HIGH:
        score += 0.15
    elif repo.stars > STARS_MEDIUM:
        score += 0.1
    if repo.last_indexed:
        days_since = _days_since(repo.last_indexed)
        if days_since < DAYS_RECENT:
            score += 0.15
        elif days_since < DAYS_MONTH:
            score += 0.1
    if repo.forks > FORKS_MODERATE:
        score += 0.1
    return min(score, 1.0)


def compute_freshness_score(issue: Issue) -> float:
    if not issue.created_at:
        return 0.3
    days_old = _days_since(issue.created_at)
    if days_old < FRESH_DAYS:
        return 1.0
    if days_old < MODERATE_DAYS:
        return 0.8
    if days_old < STALE_DAYS:
        return 0.5
    return 0.2


def compute_popularity_score(issue: Issue, repo: Repository) -> float:
    score = 0.0
    if issue.comments > COMMENTS_HIGH:
        score += 0.3
    elif issue.comments > COMMENTS_MODERATE:
        score += 0.2
    elif issue.comments > COMMENTS_LOW:
        score += 0.1
    if repo.stars > STARS_TOP:
        score += 0.4
    elif repo.stars > STARS_ACTIVE:
        score += 0.3
    elif repo.stars > STARS_KNOWN:
        score += 0.2
    elif repo.stars > STARS_MINIMAL:
        score += 0.1
    if repo.forks > FORKS_HIGH:
        score += 0.2
    elif repo.forks > FORKS_MODERATE_POP:
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
        return INTEREST_DEFAULT

    combined_user = user_langs | user_topics | user_cats | user_top
    combined_issue = issue_cats | issue_labels

    if not combined_issue:
        return INTEREST_DEFAULT

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

    if final > QUALITY_EXCELLENT:
        parts.append("Strong match")
    elif final > QUALITY_GOOD:
        parts.append("Good match")
    else:
        parts.append("Partial match")

    score_pct = round(final * 100)
    parts.append(f"({score_pct}%)")

    if matching_skills:
        skill_str = ", ".join(matching_skills[:3])
        parts.append(f"— your {skill_str} skills align")

    repo_desc: list[str] = []
    if popularity > DESC_HIGH:
        repo_desc.append("highly popular repo")
    elif popularity > DESC_MEDIUM:
        repo_desc.append("popular repo")

    if repo_activity > DESC_HIGH:
        repo_desc.append("very active")
    elif repo_activity > DESC_MEDIUM:
        repo_desc.append("active")

    if freshness > DESC_HIGH:
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

# ── Live issue scorer: sub-score weights ──────────────────────────
WEIGHT_LANG = 0.40       # language match contribution
WEIGHT_TOPIC = 0.20     # topic overlap contribution
WEIGHT_LABEL = 0.15     # label match contribution
WEIGHT_FRESHNESS = 0.15 # recency contribution
WEIGHT_POP = 0.10       # popularity contribution

# ── Live issue scorer: topic overlap multiplier ───────────────────
TOPIC_OVERLAP_MULTIPLIER = 0.35  # each matching topic adds 0.35

# ── Live issue scorer: language boost base ────────────────────────
LANG_BOOST_BASE = 0.5  # base language match score before proficiency scaling

# ── Live issue scorer: popularity thresholds (live) ──────────────
LIVE_STARS_VERY_HIGH = 10_000  # very popular repo
LIVE_STARS_HIGH = 1_000        # popular repo
LIVE_STARS_MEDIUM = 100        # moderately popular

# ── Live issue scorer: popularity increments ──────────────────────
LIVE_POP_STARS_HIGH = 0.4   # very high stars contribution
LIVE_POP_STARS_MEDIUM = 0.25 # high stars contribution
LIVE_POP_STARS_LOW = 0.1    # moderate stars contribution
LIVE_POP_FORKS_HIGH = 0.2   # many forks contribution
LIVE_POP_FORKS_LOW = 0.1    # moderate forks contribution
LIVE_POP_COMMENTS_HIGH = 0.3  # many comments contribution
LIVE_POP_COMMENTS_LOW = 0.15  # some comments contribution

# ── Live issue scorer: comment thresholds (live) ─────────────────
LIVE_COMMENTS_HIGH = 20   # many comments
LIVE_COMMENTS_MODERATE = 5  # some comments

# ── Live issue scorer: fork thresholds (live) ────────────────────
LIVE_FORKS_HIGH = 1_000  # many forks
LIVE_FORKS_MODERATE = 100  # moderate forks
LIVE_QUALITY_EXCELLENT = 0.8  # "Excellent" match threshold (live)
LIVE_QUALITY_GOOD = 0.6       # "Good" match threshold (live)

# ── Interest match defaults ──────────────────────────────────────
INTEREST_DEFAULT = 0.3  # fallback when user or issue lacks skill data


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
    # ── 1. Language match (weight 0.40)
    repo_language = (raw_repo.get("language") or "").lower()
    repo_topics = {t.lower() for t in (raw_repo.get("topics") or [])}

    lang_score = 0.0
    if repo_language and repo_language in user_languages:
        lang_pct = user_skills.get("languages", {}).get(repo_language, 0)
        lang_score = min(1.0, LANG_BOOST_BASE + lang_pct * LANG_BOOST_BASE)
    elif repo_language:
        lang_score = 0.0

    # ── 2. Topic / interest match
    topic_overlap = len(user_topics & repo_topics)
    topic_score = min(1.0, topic_overlap * TOPIC_OVERLAP_MULTIPLIER)

    # ── 3. Label match
    label_names = {lbl["name"].lower() for lbl in raw_issue.get("labels", [])}
    label_score = 0.0
    if "good first issue" in label_names:
        label_score += LABEL_BOOST_GFI
    if "help wanted" in label_names:
        label_score += LABEL_BOOST_HELP
    if "bug" in label_names:
        label_score += LABEL_BOOST_BUG
    label_score = min(1.0, label_score)

    # ── 4. Freshness
    updated_str = raw_issue.get("updated_at") or raw_issue.get("created_at", "")
    freshness_score = FRESHNESS_DEFAULT
    if updated_str:
        try:
            updated_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            age_days = _days_since(updated_dt)
            if age_days <= FRESH_DAYS:
                freshness_score = FRESHNESS_RECENT
            elif age_days <= MODERATE_DAYS:
                freshness_score = FRESHNESS_MODERATE
            elif age_days <= STALE_DAYS:
                freshness_score = FRESHNESS_STALE
            else:
                freshness_score = FRESHNESS_DEFAULT
        except (ValueError, TypeError):
            freshness_score = FRESHNESS_DEFAULT

    # ── 5. Repo popularity
    stars = raw_repo.get("stargazers_count") or raw_repo.get("stars", 0)
    forks = raw_repo.get("forks_count") or raw_repo.get("forks", 0)
    pop_score = 0.0
    if stars >= LIVE_STARS_VERY_HIGH:
        pop_score += LIVE_POP_STARS_HIGH
    elif stars >= LIVE_STARS_HIGH:
        pop_score += LIVE_POP_STARS_MEDIUM
    elif stars >= LIVE_STARS_MEDIUM:
        pop_score += LIVE_POP_STARS_LOW
    if forks >= LIVE_FORKS_HIGH:
        pop_score += LIVE_POP_FORKS_HIGH
    elif forks >= LIVE_FORKS_MODERATE:
        pop_score += LIVE_POP_FORKS_LOW
    comments = raw_issue.get("comments", 0)
    if comments >= LIVE_COMMENTS_HIGH:
        pop_score += LIVE_POP_COMMENTS_HIGH
    elif comments >= LIVE_COMMENTS_MODERATE:
        pop_score += LIVE_POP_COMMENTS_LOW
    pop_score = min(1.0, pop_score)

    # ── Composite (weights must sum to 1.0)
    composite = (
        lang_score    * WEIGHT_LANG +
        topic_score   * WEIGHT_TOPIC +
        label_score   * WEIGHT_LABEL +
        freshness_score * WEIGHT_FRESHNESS +
        pop_score     * WEIGHT_POP
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

    quality = "Excellent" if score >= LIVE_QUALITY_EXCELLENT else "Good" if score >= LIVE_QUALITY_GOOD else "Partial"
    return (
        f"{quality} match ({pct}%) — {lang} repo '{repo_name}' "
        f"[{label_str}], {stars:,} stars (live result)"
    )

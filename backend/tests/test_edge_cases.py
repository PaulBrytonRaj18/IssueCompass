"""Edge-case and boundary-value tests for all backend services."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.models import Issue, Repository
from app.services import matching_service, scoring_service
from app.services.search_service import (
    _keyword_relevance_score,
    expand_query,
    parse_natural_query,
)
from app.services.skill_service import (
    build_skill_fingerprint,
    extract_required_skills,
    issue_text_to_vector,
    skill_fingerprint_to_vector,
)

# ═══════════════════════════════════════════════════════════════════════════
# scoring_service edge cases
# ═══════════════════════════════════════════════════════════════════════════


def _make_repo(**kwargs):
    defaults = dict(
        id=1,
        github_id=1,
        full_name="owner/repo",
        name="repo",
        owner_login="owner",
        html_url="https://github.com/owner/repo",
        stars=100,
        forks=10,
        primary_language="python",
        topics=[],
        is_archived=False,
        last_indexed=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return MagicMock(spec=Repository, **defaults)


def _make_issue(**kwargs):
    defaults = dict(
        id=1,
        github_id=100,
        number=1,
        title="Test issue",
        body="Fix the bug",
        html_url="https://github.com/owner/repo/issues/1",
        state="open",
        labels=[],
        is_good_first_issue=False,
        is_help_wanted=False,
        comments=5,
        created_at=datetime.now(timezone.utc),
        required_skills={"categories": {"backend": ["python"]}, "labels": []},
    )
    defaults.update(kwargs)
    return MagicMock(spec=Issue, **defaults)


class TestScoringEdgeCases:
    """Boundary and edge-case tests for scoring functions."""

    def test_repo_activity_max_score(self):
        """Max achievable: 0.5 base + 0.2 stars + 0.15 recent + 0.1 forks = 0.95"""
        repo = _make_repo(stars=1_000_000, forks=100_000, last_indexed=datetime.now(timezone.utc))
        assert scoring_service.compute_repo_activity_score(repo) == 0.95

    def test_repo_activity_min_score(self):
        repo = _make_repo(stars=0, forks=0, last_indexed=None)
        assert scoring_service.compute_repo_activity_score(repo) == 0.5

    def test_freshness_very_old_issue(self):
        issue = _make_issue(created_at=datetime.now(timezone.utc) - timedelta(days=1000))
        assert scoring_service.compute_freshness_score(issue) == 0.2

    def test_freshness_edge_boundaries(self):
        """Test the exact boundary values (7, 30, 90 days)."""
        now = datetime.now(timezone.utc)
        assert (
            scoring_service.compute_freshness_score(_make_issue(created_at=now - timedelta(days=7)))
            == 0.8
        )
        assert (
            scoring_service.compute_freshness_score(
                _make_issue(created_at=now - timedelta(days=30))
            )
            == 0.5
        )
        assert (
            scoring_service.compute_freshness_score(
                _make_issue(created_at=now - timedelta(days=90))
            )
            == 0.2
        )

    def test_popularity_max_score(self):
        """Max achievable: 0.3 (comments>20) + 0.4 (stars>10k) + 0.2 (forks>1k) = 0.9"""
        issue = _make_issue(comments=100)
        repo = _make_repo(stars=100_000, forks=10_000)
        assert scoring_service.compute_popularity_score(issue, repo) == pytest.approx(0.9)

    def test_popularity_star_boundaries(self):
        issue = _make_issue(comments=0)
        assert (
            scoring_service.compute_popularity_score(issue, _make_repo(stars=10_001, forks=0))
            == 0.4
        )  # >10000
        assert (
            scoring_service.compute_popularity_score(issue, _make_repo(stars=10_000, forks=0))
            == 0.3
        )  # >1000
        assert (
            scoring_service.compute_popularity_score(issue, _make_repo(stars=1_001, forks=0)) == 0.3
        )  # >1000
        assert (
            scoring_service.compute_popularity_score(issue, _make_repo(stars=1_000, forks=0)) == 0.2
        )  # >100
        assert (
            scoring_service.compute_popularity_score(issue, _make_repo(stars=101, forks=0)) == 0.2
        )  # >100
        assert (
            scoring_service.compute_popularity_score(issue, _make_repo(stars=100, forks=0)) == 0.1
        )  # >10
        assert (
            scoring_service.compute_popularity_score(issue, _make_repo(stars=11, forks=0)) == 0.1
        )  # >10
        assert (
            scoring_service.compute_popularity_score(issue, _make_repo(stars=10, forks=0)) == 0.0
        )  # none
        assert (
            scoring_service.compute_popularity_score(issue, _make_repo(stars=0, forks=0)) == 0.0
        )  # none

    def test_interest_match_empty_issue_skills(self):
        user = {"languages": {"python": 0.8}, "topics": ["web"], "categories": {}, "top_skills": []}
        assert scoring_service.compute_interest_match(user, {}) == 0.3

    def test_final_score_extreme_values(self):
        """Final score is currently not clamped — weights * extreme inputs can exceed 1.0 or go negative."""
        raw = scoring_service.compute_final_score(2.0, 2.0, 2.0, 2.0, 2.0)
        assert raw > 1.0  # weights sum to 1.0, so 2.0 * 1.0 = 2.0
        raw2 = scoring_service.compute_final_score(-1.0, -1.0, -1.0, -1.0, -1.0)
        assert raw2 < 0.0

    def test_final_score_preserves_weight_distribution(self):
        """Weights should sum to 1.0."""
        total = sum(scoring_service.SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_safe_explain_score_none_values(self):
        """safe_explain_score should handle all-None inputs without crashing."""
        result = scoring_service.safe_explain_score(None, None, None, None, None, None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_safe_explain_score_catches_exception(self):
        """Should return fallback even if explain_score raises."""
        with patch("app.services.scoring_service.explain_score", side_effect=ValueError("boom")):
            result = scoring_service.safe_explain_score(0.5, 0.5, 0.5, 0.5, 0.5, ["x"])
            assert "Matched" in result

    def test_explain_score_empty_matching_skills(self):
        result = scoring_service.explain_score(0.3, 0.0, 0.1, 0.0, 0.0, [])
        assert "Partial match" in result

    def test_score_live_issue_no_repo_language(self):
        """Should not crash when repo has no language field."""
        score = scoring_service.score_live_issue(
            {"languages": {"python": 0.8}},
            {"title": "fix", "labels": [], "comments": 0},
            {"language": None, "topics": [], "stargazers_count": 0, "forks_count": 0},
        )
        assert 0.0 <= score <= 1.0

    def test_score_live_issue_malformed_dates(self):
        """Should handle invalid date strings gracefully."""
        score = scoring_service.score_live_issue(
            {"languages": {}},
            {"title": "x", "labels": [], "comments": 0, "updated_at": "not-a-date"},
            {"language": "python", "topics": [], "stargazers_count": 0, "forks_count": 0},
        )
        assert 0.0 <= score <= 1.0

    def test_score_live_issue_max_values(self):
        """All max inputs should produce a very high score."""
        score = scoring_service.score_live_issue(
            {"languages": {"python": 1.0, "go": 1.0}, "topics": ["api", "web", "cli"]},
            {
                "title": "x",
                "labels": [{"name": "good first issue"}, {"name": "help wanted"}],
                "comments": 100,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "language": "Python",
                "topics": ["api", "web", "cli"],
                "stargazers_count": 100_000,
                "forks_count": 10_000,
            },
        )
        assert score >= 0.90, f"Expected high score for max inputs, got {score}"

    def test_build_live_issue_explanation_missing_fields(self):
        """Should not crash when repo dict has missing keys."""
        result = scoring_service.build_live_issue_explanation(
            {"languages": {"python": 0.5}},
            {"title": "x", "labels": [], "comments": 0},
            {},
            0.5,
        )
        assert isinstance(result, str)
        assert "match" in result.lower()


# ═══════════════════════════════════════════════════════════════════════════
# matching_service edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestMatchingEdgeCases:
    def test_cosine_similarity_identical_large_vectors(self):
        a = [0.5] * 128
        assert matching_service.cosine_similarity(a, a) == pytest.approx(1.0, rel=1e-6)

    def test_cosine_similarity_zero_vector_input(self):
        """Zero vector should not crash (div by zero protection)."""
        assert matching_service.cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_cosine_similarity_both_zero(self):
        assert matching_service.cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0

    def test_cosine_similarity_negative_values(self):
        sim = matching_service.cosine_similarity([-1.0, 0.0], [1.0, 0.0])
        assert sim == -1.0

    def test_fingerprint_cache_key_deterministic(self):
        skills = {"languages": {"python": 0.5}, "topics": ["web"]}
        k1 = matching_service._fingerprint_cache_key(skills)
        k2 = matching_service._fingerprint_cache_key(skills)
        assert k1 == k2

    def test_fingerprint_cache_key_handles_deeply_nested(self):
        skills = {"a": {"b": {"c": [1, 2, 3]}}, "d": {"e": None}}
        key = matching_service._fingerprint_cache_key(skills)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_convert_raw_issue_no_labels(self):
        d = matching_service._convert_raw_issue_to_match_dict(
            {
                "id": 1,
                "number": 1,
                "title": "x",
                "body": "",
                "html_url": "",
                "labels": [],
                "comments": 0,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": None,
                "pull_request": None,
            },
            {
                "full_name": "a/b",
                "name": "b",
                "html_url": "",
                "language": "Go",
                "stargazers_count": 0,
                "forks_count": 0,
                "topics": [],
                "archived": False,
            },
            {"languages": {}},
            0.5,
        )
        assert d["issue"]["is_good_first_issue"] is False
        assert len(d["matching_skills"]) == 0


# ═══════════════════════════════════════════════════════════════════════════
# search_service edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestSearchEdgeCases:
    async def test_parse_query_unicode(self):
        intent = await parse_natural_query("поиск python бэкенд")
        assert intent is not None
        assert "python" in intent.languages

    async def test_parse_query_special_chars(self):
        intent = await parse_natural_query("!@#$%^&*() python backend issues")
        assert "python" in intent.languages

    async def test_parse_query_with_emoji(self):
        intent = await parse_natural_query("🐍 python bug fix")
        assert intent.keywords

    async def test_parse_query_very_long(self):
        long = "python " * 500
        intent = await parse_natural_query(long)
        assert intent is not None

    async def test_parse_query_only_stop_words(self):
        intent = await parse_natural_query("the a an in of to is")
        assert len(intent.keywords) <= 3

    async def test_keyword_relevance_score_no_keywords(self):
        intent = MagicMock()
        intent.keywords = []
        intent.languages = []
        intent.difficulty = None
        intent.labels = []
        intent.categories = []
        score = _keyword_relevance_score(
            MagicMock(title="test", body="test body", labels=[]),
            intent,
        )
        assert score == 0.3  # base score when no keywords match

    async def test_expand_query_empty_intent(self):
        intent = MagicMock(keywords=[], languages=[], difficulty=None, labels=[], categories=[])
        result = expand_query(intent)
        assert result == ""


# ═══════════════════════════════════════════════════════════════════════════
# skill_service edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestSkillEdgeCases:
    async def test_build_skill_fingerprint_empty(self):
        fp = await build_skill_fingerprint([])
        assert fp["total_repos"] == 0
        assert fp["languages"] == {}

    async def test_build_skill_fingerprint_all_forks(self):
        repos = [
            {"name": "f1", "language": "Python", "fork": True},
            {"name": "f2", "language": "Java", "fork": True},
        ]
        fp = await build_skill_fingerprint(repos)
        assert fp["total_repos"] == 0

    async def test_build_skill_fingerprint_no_language(self):
        repos = [
            {"name": "unknown", "language": None, "fork": False},
        ]
        fp = await build_skill_fingerprint(repos)
        assert fp["total_repos"] == 1

    async def test_skill_fingerprint_to_vector_empty_profile(self):
        fp = {
            "languages": {},
            "topics": [],
            "categories": {},
            "experience_level": "beginner",
            "top_skills": [],
            "total_repos": 0,
            "total_stars_received": 0,
        }
        vec = await skill_fingerprint_to_vector(fp)
        assert len(vec) == 128

    async def test_issue_text_to_vector_empty_input(self):
        vec = await issue_text_to_vector("", "", [])
        assert len(vec) == 128

    async def test_issue_text_to_vector_none_input(self):
        vec = await issue_text_to_vector(None, None, None)
        assert len(vec) == 128

    async def test_extract_required_skills_minimal(self):
        skills = await extract_required_skills("Fix", "Simple fix", [])
        assert "categories" in skills
        assert "complexity" in skills

    async def test_extract_required_skills_no_labels(self):
        skills = await extract_required_skills("Add feature", "Implement the feature", None)
        assert skills["complexity"] == 0.35  # 5 words → < 30 threshold


# ═══════════════════════════════════════════════════════════════════════════
# ai_service edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestAIEdgeCases:
    async def test_parse_query_groq_retry_then_fail(self):
        """When Groq fails repeatedly, should return None (not crash)."""
        with (
            patch("app.services.ai_service.AI_ENABLED", True),
            patch("app.services.ai_service.cache_get", new=AsyncMock(return_value=None)),
            patch("app.services.ai_service.cache_set", new=AsyncMock()),
            patch("app.services.ai_service._call_groq", new=AsyncMock(return_value=None)),
        ):
            from app.services.ai_service import parse_query_with_ai

            result = await parse_query_with_ai("test query")
            assert result is None

    async def test_parse_query_empty_cache_miss_fallback(self):
        """With AI disabled, should return None immediately."""
        with patch("app.services.ai_service.AI_ENABLED", False):
            from app.services.ai_service import parse_query_with_ai

            result = await parse_query_with_ai("test")
            assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# github_service edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestGithubEdgeCases:
    async def test_fetch_user_returned_none(self):
        """A 404 response should propagate as None."""
        from app.services.github_service import fetch_user

        mock_resp = MagicMock(status_code=404, headers={})
        with patch(
            "app.services.github_service._gh_request", new=AsyncMock(return_value=mock_resp)
        ):
            result = await fetch_user("nobody")
            assert result is None

    async def test_search_issues_global_empty_response(self):
        """Empty search should still return a dict, not crash."""
        from app.services.github_service import search_issues_global

        mock_resp = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "100"})
        mock_resp.json = MagicMock(return_value={"items": [], "total_count": 0})
        with patch(
            "app.services.github_service._gh_request", new=AsyncMock(return_value=mock_resp)
        ):
            result = await search_issues_global()
            assert isinstance(result, dict)
            assert result["items"] == []


# ═══════════════════════════════════════════════════════════════════════════
# worker edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestWorkerEdgeCases:
    async def test_full_index_no_languages(self):
        """Should handle empty language list gracefully."""
        from app.worker import full_index

        with patch("app.core.cache.cache_delete_pattern", new=AsyncMock()):
            result = await full_index({}, languages=[])
            assert result["total_indexed"] == 0

    async def test_cleanup_stale_zero_rows(self):
        """Should not crash when no stale issues exist."""
        from app.worker import cleanup_stale_issues_task

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        await cleanup_stale_issues_task({"db": mock_db})
        assert mock_db.execute.called
        assert mock_db.commit.called

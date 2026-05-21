from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.models.models import Issue
from app.services import matching_service, scoring_service


def test_cosine_similarity_identical():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert matching_service.cosine_similarity(a, b) == 1.0


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert matching_service.cosine_similarity(a, b) == 0.0


def test_cosine_similarity_zero_vector():
    a = [0.0, 0.0]
    b = [1.0, 0.0]
    assert matching_service.cosine_similarity(a, b) == 0.0


def test_cosine_similarity_partial():
    a = [1.0, 1.0]
    b = [1.0, 0.0]
    result = matching_service.cosine_similarity(a, b)
    assert 0.5 < result < 1.0


def test_explain_score_strong():
    text = scoring_service.explain_score(
        skill_similarity=1.0,
        repo_activity=1.0,
        freshness=1.0,
        interest_match=1.0,
        popularity=1.0,
        matching_skills=["python"],
    )
    assert "Strong match" in text
    assert "python" in text


def test_explain_score_good():
    text = scoring_service.explain_score(
        skill_similarity=0.7,
        repo_activity=0.5,
        freshness=0.5,
        interest_match=0.5,
        popularity=0.5,
        matching_skills=["python"],
    )
    assert "Good match" in text


def test_explain_score_partial():
    text = scoring_service.explain_score(
        skill_similarity=0.2,
        repo_activity=0.0,
        freshness=0.1,
        interest_match=0.0,
        popularity=0.0,
        matching_skills=[],
    )
    assert "Partial match" in text


def test_keyword_score_match():
    from app.models.models import Issue
    issue = Issue(
        id=1,
        github_id=1,
        number=1,
        title="Build a Python API",
        body="Using Django framework",
        html_url="https://example.com",
    )
    user_skills = {"languages": {"python": 1.0, "django": 0.5}, "topics": ["api"]}
    score = matching_service._keyword_score(user_skills, issue)
    assert score > 0


def test_keyword_score_no_match():
    from app.models.models import Issue
    issue = Issue(
        id=2,
        github_id=2,
        number=2,
        title="Rust systems programming",
        body="Low-level memory management",
        html_url="https://example.com",
    )
    user_skills = {"languages": {"python": 1.0}, "topics": ["web"]}
    score = matching_service._keyword_score(user_skills, issue)
    assert score == 0


class TestFingerprintCacheKey:
    """Tests for the Redis cache key generator."""

    def test_key_is_order_independent(self):
        a = matching_service._fingerprint_cache_key({"languages": {"python": 0.6, "typescript": 0.4}})
        b = matching_service._fingerprint_cache_key({"languages": {"typescript": 0.4, "python": 0.6}})
        assert a == b

    def test_key_starts_with_prefix(self):
        key = matching_service._fingerprint_cache_key({"languages": {"rust": 1.0}})
        assert key.startswith("live_matches:")

    def test_different_skills_produce_different_keys(self):
        key_a = matching_service._fingerprint_cache_key({"languages": {"python": 1.0}})
        key_b = matching_service._fingerprint_cache_key({"languages": {"rust": 1.0}})
        assert key_a != key_b

    def test_empty_skill_json_does_not_crash(self):
        key = matching_service._fingerprint_cache_key({})
        assert isinstance(key, str) and len(key) > 0


class TestConvertRawIssueToMatchDict:
    """Tests for the live-issue shape converter."""

    RAW_ISSUE = {
        "id": 123456789,
        "number": 42,
        "title": "Fix null pointer in parser",
        "body": "Steps to reproduce...",
        "html_url": "https://github.com/org/repo/issues/42",
        "labels": [{"name": "good first issue"}],
        "comments": 5,
        "created_at": "2025-04-01T00:00:00Z",
        "updated_at": "2025-05-01T00:00:00Z",
        "pull_request": None,
    }
    RAW_REPO = {
        "full_name": "org/repo",
        "name": "repo",
        "html_url": "https://github.com/org/repo",
        "language": "Go",
        "stargazers_count": 2000,
        "forks_count": 150,
        "topics": ["cli", "tooling"],
        "archived": False,
    }
    USER_SKILLS = {
        "languages": {"go": 0.9},
        "topics": ["cli"],
        "top_skills": ["golang"],
    }

    def test_produces_required_keys(self):
        d = matching_service._convert_raw_issue_to_match_dict(self.RAW_ISSUE, self.RAW_REPO, self.USER_SKILLS, 0.75)
        required = ["match_score", "_is_live", "is_live_result", "issue", "repository"]
        for key in required:
            assert key in d, f"Missing key: {key}"

    def test_is_live_flag_is_true(self):
        d = matching_service._convert_raw_issue_to_match_dict(self.RAW_ISSUE, self.RAW_REPO, self.USER_SKILLS, 0.75)
        assert d["_is_live"] is True
        assert d["is_live_result"] is True

    def test_good_first_issue_flag_set(self):
        d = matching_service._convert_raw_issue_to_match_dict(self.RAW_ISSUE, self.RAW_REPO, self.USER_SKILLS, 0.75)
        assert d["issue"]["is_good_first_issue"] is True

    def test_matching_skills_contains_overlap(self):
        d = matching_service._convert_raw_issue_to_match_dict(self.RAW_ISSUE, self.RAW_REPO, self.USER_SKILLS, 0.75)
        assert "go" in d["matching_skills"] or "cli" in d["matching_skills"]

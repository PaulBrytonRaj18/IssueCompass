from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.models.models import Issue, Repository
from app.services import scoring_service


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


# ── compute_repo_activity_score ─────────────────────────────────


def test_archived_repo_scores_zero():
    repo = _make_repo(is_archived=True)
    assert scoring_service.compute_repo_activity_score(repo) == 0.0


def test_high_stars_boosts_activity():
    repo = _make_repo(stars=50000, forks=200, last_indexed=datetime.now(timezone.utc))
    score = scoring_service.compute_repo_activity_score(repo)
    assert 0.5 < score <= 1.0


def test_stale_repo_loses_activity_points():
    from datetime import timedelta
    repo = _make_repo(stars=50, last_indexed=datetime.now(timezone.utc) - timedelta(days=60))
    score = scoring_service.compute_repo_activity_score(repo)
    assert score <= 0.7


# ── compute_freshness_score ─────────────────────────────────────


def test_recent_issue_scores_max():
    issue = _make_issue(created_at=datetime.now(timezone.utc))
    assert scoring_service.compute_freshness_score(issue) == 1.0


def test_old_issue_decays():
    from datetime import timedelta
    issue = _make_issue(created_at=datetime.now(timezone.utc) - timedelta(days=200))
    assert scoring_service.compute_freshness_score(issue) == 0.2


def test_no_created_at_freshness():
    issue = _make_issue(created_at=None)
    assert scoring_service.compute_freshness_score(issue) == 0.3


# ── compute_popularity_score ────────────────────────────────────


def test_popularity_high_stars_many_comments():
    issue = _make_issue(comments=25)
    repo = _make_repo(stars=20000, forks=2000)
    score = scoring_service.compute_popularity_score(issue, repo)
    assert score > 0.5


def test_popularity_low():
    issue = _make_issue(comments=0)
    repo = _make_repo(stars=1, forks=0)
    score = scoring_service.compute_popularity_score(issue, repo)
    assert score == 0.0


# ── compute_interest_match ──────────────────────────────────────


def test_interest_match_high_overlap():
    user_skills = {
        "languages": {"python": 0.8, "javascript": 0.2},
        "topics": ["machine-learning"],
        "categories": {},
        "top_skills": ["python", "machine-learning"],
    }
    issue_skills = {
        "categories": {"ai_ml": ["python", "pytorch"]},
        "labels": ["machine-learning"],
    }
    score = scoring_service.compute_interest_match(user_skills, issue_skills)
    assert score > 0.3


def test_interest_match_no_overlap():
    user_skills = {
        "languages": {"ruby": 1.0},
        "topics": [],
        "categories": {},
        "top_skills": ["ruby"],
    }
    issue_skills = {
        "categories": {"frontend": ["javascript"]},
        "labels": ["react"],
    }
    score = scoring_service.compute_interest_match(user_skills, issue_skills)
    assert score <= 0.4


def test_interest_match_empty_user_skills():
    user_skills = {"languages": {}, "topics": [], "categories": {}, "top_skills": []}
    issue_skills = {"categories": {"backend": ["python"]}, "labels": ["api"]}
    score = scoring_service.compute_interest_match(user_skills, issue_skills)
    assert score == 0.3


# ── compute_final_score ─────────────────────────────────────────


def test_final_score_perfect():
    score = scoring_service.compute_final_score(
        skill_similarity=1.0,
        repo_activity=1.0,
        freshness=1.0,
        interest_match=1.0,
        popularity=1.0,
    )
    assert score == 1.0


def test_final_score_zero():
    score = scoring_service.compute_final_score(
        skill_similarity=0.0,
        repo_activity=0.0,
        freshness=0.0,
        interest_match=0.0,
        popularity=0.0,
    )
    assert score == 0.0


def test_final_score_weighted():
    score = scoring_service.compute_final_score(
        skill_similarity=1.0,
        repo_activity=0.0,
        freshness=0.0,
        interest_match=0.0,
        popularity=0.0,
    )
    assert score == scoring_service.SCORE_WEIGHTS["skill_match"]


# ── explain_score ───────────────────────────────────────────────


def test_explain_score_strong():
    text = scoring_service.explain_score(
        skill_similarity=1.0,
        repo_activity=1.0,
        freshness=1.0,
        interest_match=1.0,
        popularity=1.0,
        matching_skills=["python", "fastapi"],
    )
    assert "Strong match" in text
    assert "python" in text


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


class TestScoreLiveIssue:
    """Tests for the new proxy scorer for live GitHub issues."""

    BASE_USER_SKILLS = {
        "languages": {"python": 0.7, "typescript": 0.3},
        "topics": ["web", "api"],
        "top_skills": ["fastapi", "react"],
        "categories": {"backend": 0.6, "frontend": 0.4},
        "experience_level": "intermediate",
    }

    BASE_REPO = {
        "language": "Python",
        "topics": ["api", "web"],
        "stargazers_count": 5000,
        "forks_count": 300,
        "full_name": "testorg/testrepo",
        "name": "testrepo",
        "archived": False,
    }

    BASE_ISSUE = {
        "title": "Fix authentication bug",
        "body": "The login endpoint returns 500 on empty password.",
        "labels": [{"name": "good first issue"}, {"name": "bug"}],
        "updated_at": "2025-05-01T00:00:00Z",
        "created_at": "2025-04-28T00:00:00Z",
        "comments": 8,
        "pull_request": None,
    }

    def test_pull_request_always_scores_zero(self):
        issue_as_pr = {**self.BASE_ISSUE, "pull_request": {"url": "https://..."}}
        score = scoring_service.score_live_issue(self.BASE_USER_SKILLS, issue_as_pr, self.BASE_REPO)
        assert score == 0.0

    def test_perfect_language_match_scores_high(self):
        score = scoring_service.score_live_issue(self.BASE_USER_SKILLS, self.BASE_ISSUE, self.BASE_REPO)
        assert score >= 0.55, f"Expected strong match, got {score}"

    def test_language_mismatch_scores_lower(self):
        repo_rust = {**self.BASE_REPO, "language": "Rust", "topics": []}
        score = scoring_service.score_live_issue(self.BASE_USER_SKILLS, self.BASE_ISSUE, repo_rust)
        assert score <= 0.45, f"Expected weak match for unknown lang, got {score}"

    def test_good_first_issue_label_increases_score(self):
        issue_no_label = {**self.BASE_ISSUE, "labels": []}
        score_with    = scoring_service.score_live_issue(self.BASE_USER_SKILLS, self.BASE_ISSUE, self.BASE_REPO)
        score_without = scoring_service.score_live_issue(self.BASE_USER_SKILLS, issue_no_label, self.BASE_REPO)
        assert score_with > score_without

    def test_stale_issue_scores_lower_than_fresh(self):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(days=200)).isoformat()
        fresh_date = (now - timedelta(days=1)).isoformat()
        fresh_issue = {**self.BASE_ISSUE, "updated_at": fresh_date}
        stale_issue = {**self.BASE_ISSUE, "updated_at": old_date}
        score_fresh = scoring_service.score_live_issue(self.BASE_USER_SKILLS, fresh_issue, self.BASE_REPO)
        score_stale = scoring_service.score_live_issue(self.BASE_USER_SKILLS, stale_issue, self.BASE_REPO)
        assert score_fresh > score_stale

    def test_empty_skill_json_returns_low_score(self):
        score = scoring_service.score_live_issue({}, self.BASE_ISSUE, self.BASE_REPO)
        assert score < 0.30

    def test_score_is_clamped_between_zero_and_one(self):
        score = scoring_service.score_live_issue(self.BASE_USER_SKILLS, self.BASE_ISSUE, self.BASE_REPO)
        assert 0.0 <= score <= 1.0

    def test_missing_updated_at_does_not_crash(self):
        issue_no_date = {**self.BASE_ISSUE, "updated_at": None, "created_at": None}
        score = scoring_service.score_live_issue(self.BASE_USER_SKILLS, issue_no_date, self.BASE_REPO)
        assert 0.0 <= score <= 1.0

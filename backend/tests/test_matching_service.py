import pytest
from app.services.matching_service import cosine_similarity, explain_match, _keyword_score


def test_cosine_similarity_identical():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == 1.0


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == 0.0


def test_cosine_similarity_zero_vector():
    a = [0.0, 0.0]
    b = [1.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


def test_cosine_similarity_partial():
    a = [1.0, 1.0]
    b = [1.0, 0.0]
    result = cosine_similarity(a, b)
    assert 0.5 < result < 1.0


def test_explain_match_strong():
    user_skills = {"languages": {"python": 1.0}, "topics": ["api"], "top_skills": ["python"]}
    issue_skills = {"categories": {"backend": ["python", "django"]}, "labels": ["backend"]}
    matching, why = explain_match(user_skills, issue_skills, 0.9)
    assert "python" in matching
    assert "Strong match" in why


def test_explain_match_good():
    user_skills = {"languages": {"python": 1.0}, "topics": [], "top_skills": ["python"]}
    issue_skills = {"categories": {"backend": ["python"]}, "labels": []}
    matching, why = explain_match(user_skills, issue_skills, 0.6)
    assert "python" in matching
    assert "Good match" in why


def test_explain_match_partial():
    user_skills = {"languages": {"java": 1.0}, "topics": [], "top_skills": ["java"]}
    issue_skills = {"categories": {"backend": ["python"]}, "labels": ["good first issue"]}
    matching, why = explain_match(user_skills, issue_skills, 0.3)
    assert "Partial match" in why


def test_keyword_score_match():
    from app.models.models import Issue
    import uuid
    issue = Issue(
        id=1,
        github_id=1,
        number=1,
        title="Build a Python API",
        body="Using Django framework",
        html_url="https://example.com",
    )
    user_skills = {"languages": {"python": 1.0, "django": 0.5}, "topics": ["api"]}
    score = _keyword_score(user_skills, issue)
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
    score = _keyword_score(user_skills, issue)
    assert score == 0

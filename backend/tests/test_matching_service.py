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

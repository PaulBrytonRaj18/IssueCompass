from app.services.search_service import (
    SearchIntent,
    expand_query,
    parse_natural_query,
    _keyword_relevance_score,
)
from app.models.models import Issue


# ── parse_natural_query ────────────────────────────────────────


def test_parse_query_detects_language():
    intent = parse_natural_query("python backend issues")
    assert "python" in intent.languages
    assert "backend" in intent.categories


def test_parse_query_detects_difficulty():
    intent = parse_natural_query("beginner React issues for newcomers")
    assert intent.difficulty == "beginner"
    assert "react" in intent.languages or "javascript" in intent.languages


def test_parse_query_detects_advanced():
    intent = parse_natural_query("complex advanced kernel module")
    assert intent.difficulty == "advanced"
    assert "systems" in intent.categories


def test_parse_query_detects_labels():
    intent = parse_natural_query("good first issue for beginners")
    assert intent.difficulty == "beginner"
    assert "good_first" in intent.labels


def test_parse_query_extracts_keywords():
    intent = parse_natural_query("fix authentication bug in FastAPI")
    assert "fastapi" in intent.languages or "python" in intent.languages
    assert intent.keywords == ["fix", "authentication", "bug"]


def test_parse_query_empty():
    intent = parse_natural_query("")
    assert intent.is_empty


def test_parse_query_technical_query():
    intent = parse_natural_query("TypeScript React frontend UI fixes")
    assert "typescript" in intent.languages or "javascript" in intent.languages
    assert "frontend" in intent.categories
    assert "fixes" in intent.keywords


def test_parse_query_docker():
    intent = parse_natural_query("Docker compose deployment help wanted")
    assert "docker" in intent.languages
    assert "help_wanted" in intent.labels


def test_parse_query_full_stack():
    intent = parse_natural_query("full stack web development tasks for intermediate")
    assert intent.difficulty == "intermediate" or intent.difficulty == "beginner"
    assert "frontend" in intent.categories or "backend" in intent.categories


# ── expand_query ───────────────────────────────────────────────


def test_expand_query():
    intent = SearchIntent(
        keywords=["fix", "bug"],
        languages=["python"],
        difficulty="beginner",
    )
    expanded = expand_query(intent)
    assert "fix" in expanded
    assert "bug" in expanded
    assert "python" in expanded


# ── _keyword_relevance_score ────────────────────────────────────


def test_keyword_relevance_score():
    intent = parse_natural_query("python api bug")
    issue = Issue(
        id=1,
        github_id=1,
        number=1,
        title="Fix API bug in Python backend",
        body="There is a bug in the API",
        html_url="https://example.com",
        labels=["bug"],
    )
    score = _keyword_relevance_score(issue, intent)
    assert score > 0.5


def test_keyword_relevance_score_no_match():
    intent = parse_natural_query("rust systems programming")
    issue = Issue(
        id=2,
        github_id=2,
        number=2,
        title="React frontend UI component",
        body="Building a button component",
        html_url="https://example.com",
        labels=["frontend"],
    )
    score = _keyword_relevance_score(issue, intent)
    assert score < 0.5

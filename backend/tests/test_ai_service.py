"""Tests for the AI service module with mocked external APIs."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from app.services.ai_service import (
    _cached_ai_call,
    _call_groq,
    _call_jina_embed,
    _parse_json_response,
    analyze_issue_with_ai,
    analyze_skills_with_ai,
    close_client,
    generate_embedding,
    generate_match_explanation,
    generate_vector_text,
    parse_query_with_ai,
)


@pytest.mark.asyncio
async def test_parse_query_with_ai_disabled():
    with patch("app.services.ai_service.AI_ENABLED", False):
        result = await parse_query_with_ai("python bug fix")
        assert result is None


@pytest.mark.asyncio
async def test_parse_query_with_ai_enabled():
    mock_groq_response = json.dumps(
        {
            "keywords": ["bug"],
            "languages": ["python"],
            "difficulty": "beginner",
            "labels": ["bug"],
            "categories": ["backend"],
            "expanded_query": "test",
        }
    )
    with (
        patch("app.services.ai_service.AI_ENABLED", True),
        patch("app.services.ai_service._call_groq", new=AsyncMock(return_value=mock_groq_response)),
        patch("app.services.ai_service.cache_get", new=AsyncMock(return_value=None)),
        patch("app.services.ai_service.cache_set", new=AsyncMock()),
    ):
        result = await parse_query_with_ai("python bug fix")
        assert result is not None
        assert result["languages"] == ["python"]
        assert result["difficulty"] == "beginner"


@pytest.mark.asyncio
async def test_parse_query_returns_none_on_bad_json():
    with (
        patch("app.services.ai_service.AI_ENABLED", True),
        patch("app.services.ai_service._call_groq", new=AsyncMock(return_value="not json at all")),
        patch("app.services.ai_service.cache_get", new=AsyncMock(return_value=None)),
        patch("app.services.ai_service.cache_set", new=AsyncMock()),
    ):
        result = await parse_query_with_ai("some query")
        assert result is None


@pytest.mark.asyncio
async def test_parse_query_with_cached_result():
    cached = {
        "keywords": ["test"],
        "languages": [],
        "difficulty": None,
        "labels": [],
        "categories": [],
        "expanded_query": "",
    }
    with (
        patch("app.services.ai_service.AI_ENABLED", True),
        patch("app.services.ai_service.cache_get", new=AsyncMock(return_value=cached)),
        patch(
            "app.services.ai_service._call_groq",
            new=AsyncMock(side_effect=RuntimeError("should not be called")),
        ),
    ):
        result = await parse_query_with_ai("cached query")
        assert result == cached


# ── _parse_json_response ────────────────────────────────────────────


class TestParseJsonResponse:
    async def test_parses_valid_json(self):
        result = await _parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    async def test_returns_empty_dict_on_none(self):
        result = await _parse_json_response(None)
        assert result == {}

    async def test_returns_empty_dict_on_empty_string(self):
        result = await _parse_json_response("")
        assert result == {}

    async def test_extracts_json_from_markdown_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        result = await _parse_json_response(raw)
        assert result == {"key": "value"}

    async def test_extracts_embedded_json_from_text(self):
        raw = 'Some text before {"key": "value"} and after'
        result = await _parse_json_response(raw)
        assert result == {"key": "value"}

    async def test_returns_empty_dict_on_completely_unparseable(self):
        result = await _parse_json_response("This is just text without any JSON")
        assert result == {}


# ── _call_groq ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_call_groq_raises_when_ai_disabled():
    with patch("app.services.ai_service.AI_ENABLED", False):
        with pytest.raises(Exception):
            await _call_groq("prompt", "query")


@pytest.mark.asyncio
async def test_cached_ai_call_returns_cached():
    cache_get = AsyncMock(return_value={"cached": "data"})
    with patch("app.services.ai_service.cache_get", cache_get):
        result = await _cached_ai_call("key", 3600, lambda: "never called")
        assert result == {"cached": "data"}


@pytest.mark.asyncio
async def test_cached_ai_call_dedup_in_flight():
    call_count = 0

    async def slow_factory():
        nonlocal call_count
        call_count += 1
        return {"computed": call_count}

    with (
        patch("app.services.ai_service.cache_get", new=AsyncMock(return_value=None)),
        patch("app.services.ai_service.cache_set", new=AsyncMock()),
    ):
        from app.services.ai_service import _in_flight

        _in_flight.clear()
        await _cached_ai_call("dedup", 3600, slow_factory)


# ── analyze_skills_with_ai ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_skills_returns_none_when_disabled():
    with patch("app.services.ai_service.AI_ENABLED", False):
        result = await analyze_skills_with_ai([{"name": "test", "language": "python"}])
        assert result is None


@pytest.mark.asyncio
async def test_analyze_skills_returns_none_for_empty_repos():
    result = await analyze_skills_with_ai([])
    assert result is None


# ── analyze_issue_with_ai ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_issue_returns_none_when_disabled():
    with patch("app.services.ai_service.AI_ENABLED", False):
        result = await analyze_issue_with_ai("title", "body", ["bug"])
        assert result is None


# ── generate_match_explanation ──────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_match_explanation_disabled():
    with patch("app.services.ai_service.AI_ENABLED", False):
        result = await generate_match_explanation(
            {"top_skills": ["python"]}, {"skills": ["python"]}, 0.9
        )
        assert result is None


# ── generate_vector_text ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_vector_text_disabled():
    with patch("app.services.ai_service.AI_ENABLED", False):
        result = await generate_vector_text({"languages": {"python": 1.0}})
        assert result is None


# ── generate_embedding ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_embedding_disabled():
    with patch("app.services.ai_service.EMBEDDINGS_ENABLED", False):
        result = await generate_embedding("some text")
        assert result is None


@pytest.mark.asyncio
async def test_generate_embedding_empty_text():
    result = await generate_embedding("")
    assert result is None


@pytest.mark.asyncio
async def test_generate_embedding_returns_cached():
    cached = [0.1, 0.2, 0.3]
    with (
        patch("app.services.ai_service.EMBEDDINGS_ENABLED", True),
        patch("app.services.ai_service.cache_get", new=AsyncMock(return_value=cached)),
    ):
        result = await generate_embedding("test")
        assert result == cached


# ── _call_jina_embed ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_call_jina_embed_disabled():
    with patch("app.services.ai_service.EMBEDDINGS_ENABLED", False):
        result = await _call_jina_embed("text")
        assert result is None


# ── close_client ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_close_client_does_not_raise():
    await close_client()

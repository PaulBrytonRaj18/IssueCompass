"""Tests for the AI service module with mocked external APIs."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai_service import (
    AI_ENABLED,
    EMBEDDINGS_ENABLED,
    parse_query_with_ai,
)


@pytest.mark.asyncio
async def test_parse_query_with_ai_disabled():
    """Should return None when AI is disabled."""
    with patch("app.services.ai_service.AI_ENABLED", False):
        result = await parse_query_with_ai("python bug fix")
        assert result is None


@pytest.mark.asyncio
async def test_parse_query_with_ai_enabled():
    """Should parse a query when AI is enabled and Groq responds."""
    mock_result = {
        "languages": ["python"],
        "difficulty": "beginner",
        "labels": ["bug"],
        "keywords": ["bug", "fix"],
        "categories": ["backend"],
        "expanded_query": "python bug fix language:python",
    }
    with (
        patch("app.services.ai_service.AI_ENABLED", True),
        patch("app.services.ai_service._call_groq", new=AsyncMock(return_value='{"keywords": ["bug"], "languages": ["python"], "difficulty": "beginner", "labels": ["bug"], "categories": ["backend"], "expanded_query": "test"}')),
        patch("app.services.ai_service.cache_get", new=AsyncMock(return_value=None)),
        patch("app.services.ai_service.cache_set", new=AsyncMock()),
    ):
        result = await parse_query_with_ai("python bug fix")
        assert result is not None
        assert result["languages"] == ["python"]
        assert result["difficulty"] == "beginner"


@pytest.mark.asyncio
async def test_parse_query_returns_none_on_bad_json():
    """Should return None when Groq returns unparseable JSON."""
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
    """Should return cached result without calling Groq."""
    cached = {"keywords": ["test"], "languages": [], "difficulty": None, "labels": [], "categories": [], "expanded_query": ""}
    with (
        patch("app.services.ai_service.AI_ENABLED", True),
        patch("app.services.ai_service.cache_get", new=AsyncMock(return_value=cached)),
        patch("app.services.ai_service._call_groq", new=AsyncMock(side_effect=RuntimeError("should not be called"))),
    ):
        result = await parse_query_with_ai("cached query")
        assert result == cached

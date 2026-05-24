"""Tests for the ARQ background worker module with mocked dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.worker import (
    cleanup_stale_issues_task,
    full_index,
    index_issues_task,
    _parse_redis_url,
)


class TestParseRedisUrl:
    def test_standard_url(self):
        result = _parse_redis_url("redis://localhost:6379")
        assert result["host"] == "localhost"
        assert result["port"] == 6379

    def test_url_with_password(self):
        result = _parse_redis_url("redis://:secret@host:6380")
        assert result["host"] == "host"
        assert result["port"] == 6380
        assert result["password"] == "secret"

    def test_url_with_username(self):
        result = _parse_redis_url("redis://user@host:6379")
        assert result["host"] == "host"
        assert result["username"] == "user"

    def test_ssl_url(self):
        result = _parse_redis_url("rediss://localhost:6379")
        assert result["ssl"] is True

    def test_invalid_url_falls_back(self):
        result = _parse_redis_url("")
        assert result["host"] == "localhost"
        assert result["port"] == 6379

    def test_default_port(self):
        result = _parse_redis_url("redis://host")
        assert result["port"] == 6379


@pytest.mark.asyncio
async def test_full_index_calls_index_language():
    """full_index should orchestrate indexing across languages and labels."""
    mock_ctx = {}

    with (
        patch("app.worker.index_language_issues", new=AsyncMock(return_value={"indexed": 1})),
        patch("app.core.cache.cache_delete_pattern", new=AsyncMock()),
    ):
        result = await full_index(mock_ctx, languages=["python"])
        assert result["total_indexed"] > 0
        assert "python" in result["languages"]


@pytest.mark.asyncio
async def test_cleanup_stale_issues_task():
    """cleanup_stale_issues_task should execute the DELETE query."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [1, 2, 3]
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    ctx = {"db": mock_db}
    await cleanup_stale_issues_task(ctx)
    assert mock_db.execute.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_index_issues_task_uses_db():
    """index_issues_task should query user languages from the database."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("python", 5), ("typescript", 3)]
    mock_db.execute = AsyncMock(return_value=mock_result)

    ctx = {"db": mock_db}

    with patch("app.worker.index_language_issues", new=AsyncMock(return_value={"indexed": 1})):
        await index_issues_task(ctx)
        assert mock_db.execute.called

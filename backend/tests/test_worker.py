"""Tests for the ARQ background worker module with mocked dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.worker import (
    cleanup_stale_issues_task,
    full_index,
    index_issues_task,
    index_language_issues,
    _parse_redis_url,
    shutdown,
    startup,
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


class TestWorkerLifecycle:
    @pytest.mark.asyncio
    async def test_startup(self):
        with patch("app.worker.init_redis", new=AsyncMock()):
            result = await startup({})
            assert result is None

    @pytest.mark.asyncio
    async def test_shutdown(self):
        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with (
            patch("app.worker.close_redis", new=AsyncMock()),
            patch("app.worker.db_engine", mock_engine),
        ):
            result = await shutdown({})
            assert result is None


class TestFullIndex:
    @pytest.mark.asyncio
    async def test_full_index_calls_index_language(self):
        mock_ctx = {}
        with (
            patch("app.worker.index_language_issues", new=AsyncMock(return_value={"indexed": 1})),
            patch("app.core.cache.cache_delete_pattern", new=AsyncMock()),
        ):
            result = await full_index(mock_ctx, languages=["python"])
            assert result["total_indexed"] > 0
            assert "python" in result["languages"]

    @pytest.mark.asyncio
    async def test_full_index_empty_languages(self):
        mock_ctx = {}
        with (
            patch("app.worker.index_language_issues", new=AsyncMock(return_value={"indexed": 0})),
        ):
            result = await full_index(mock_ctx, languages=[])
            assert result["total_indexed"] == 0

    @pytest.mark.asyncio
    async def test_full_index_default_languages(self):
        mock_ctx = {}
        with (
            patch("app.worker.index_language_issues", new=AsyncMock(return_value={"indexed": 0})),
            patch("app.core.cache.cache_delete_pattern", new=AsyncMock()),
        ):
            result = await full_index(mock_ctx, languages=None)
            assert len(result["languages"]) == 5  # defaults: python, js, ts, go, rust


class TestIndexLanguageIssues:
    @pytest.mark.asyncio
    async def test_index_language_returns_summary(self):
        with (
            patch("app.services.github_service.search_issues_global", new=AsyncMock(return_value={"items": []})),
        ):
            result = await index_language_issues({}, "python", "good first issue")
            assert result["language"] == "python"
            assert result["indexed"] == 0

    @pytest.mark.asyncio
    async def test_index_language_handles_exception(self):
        with patch("app.services.github_service.search_issues_global", new=AsyncMock(side_effect=Exception("API error"))):
            result = await index_language_issues({}, "python", "good first issue")
            assert result["error"] is not None
            assert result["indexed"] == 0


class TestIndexIssuesTask:
    @pytest.mark.asyncio
    async def test_index_issues_task_uses_db(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("python", 5), ("typescript", 3)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        ctx = {"db": mock_db}

        with patch("app.worker.index_language_issues", new=AsyncMock(return_value={"indexed": 1})):
            await index_issues_task(ctx)
            assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_index_issues_task_empty_db(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        ctx = {"db": mock_db}

        with patch("app.worker.index_language_issues", new=AsyncMock(return_value={"indexed": 0})):
            await index_issues_task(ctx)
            assert mock_db.execute.called


class TestCleanupStaleIssues:
    @pytest.mark.asyncio
    async def test_cleanup_stale_issues_task(self):
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
    async def test_cleanup_stale_issues_handles_exception(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_db.rollback = AsyncMock()

        ctx = {"db": mock_db}
        await cleanup_stale_issues_task(ctx)
        assert mock_db.rollback.called

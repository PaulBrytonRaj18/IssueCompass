import json
from unittest.mock import AsyncMock, patch

from app.core.cache import (
    PREFIX,
    _key,
    _record_latency,
    _should_early_expire,
    cache_delete,
    cache_delete_pattern,
    cache_exists,
    cache_get,
    cache_get_with_stale,
    cache_health,
    cache_ping,
    cache_set,
    cache_stats,
    cache_ttl,
    close_redis,
    init_redis,
)

_clean_globals = {
    "_redis": None,
    "_available": False,
    "_hits": 0,
    "_misses": 0,
    "_cache_latencies": [],
    "_in_flight": {},
}


def _reset_cache_globals(monkeypatch):
    for name, val in _clean_globals.items():
        monkeypatch.setattr(f"app.core.cache.{name}", val, raising=False)


def _mock_redis_client(**kwargs) -> AsyncMock:
    client = AsyncMock()
    for attr, val in kwargs.items():
        setattr(client, attr, val)
    return client


# ── _key ──────────────────────────────────────────────────────────


class TestKeyPrefix:
    def test_applies_prefix(self):
        assert _key("foo") == f"{PREFIX}foo"


# ── _should_early_expire ──────────────────────────────────────────


class TestShouldEarlyExpire:
    def test_expired_ttl_always_true(self):
        assert _should_early_expire(0.0) is True
        assert _should_early_expire(-1.0) is True

    def test_high_ttl_rarely_true(self):
        results = [_should_early_expire(3600) for _ in range(1000)]
        true_count = sum(results)
        assert true_count < 200, f"Expected few early expires, got {true_count}/1000"

    def test_low_ttl_often_true(self):
        results = [_should_early_expire(1) for _ in range(1000)]
        true_count = sum(results)
        assert true_count > 50, f"Expected some early expires, got {true_count}/1000"

    def test_zero_ttl_triggers_immediately(self):
        assert _should_early_expire(0) is True


# ── _record_latency ───────────────────────────────────────────────


class TestRecordLatency:
    def test_appends_to_rolling_window(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        _record_latency(0.1)
        _record_latency(0.2)
        stats = cache_stats()
        assert stats["avg_latency_ms"] > 0
        assert stats["p99_latency_ms"] > 0


# ── init_redis / close_redis ──────────────────────────────────────


class TestRedisLifecycle:
    @patch("app.core.cache.aioredis.from_url")
    async def test_init_success(self, mock_from_url, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_from_url.return_value = mock_redis

        await init_redis()
        stats = cache_stats()
        assert stats["available"] is True

    @patch("app.core.cache.aioredis.from_url")
    async def test_init_failure_marks_unavailable(self, mock_from_url, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock_from_url.side_effect = ConnectionError("no redis")

        await init_redis()
        stats = cache_stats()
        assert stats["available"] is False

    async def test_close_clears_state(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._redis", AsyncMock())
        monkeypatch.setattr("app.core.cache._available", True)

        await close_redis()
        stats = cache_stats()
        assert stats["available"] is False


# ── cache_get ─────────────────────────────────────────────────────


class TestCacheGet:
    async def test_returns_none_when_redis_unavailable(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", False)
        assert await cache_get("x") is None

    async def test_returns_none_on_miss(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.get.return_value = None
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        result = await cache_get("missing")
        assert result is None
        stats = cache_stats()
        assert stats["misses"] >= 1

    async def test_returns_value_on_hit(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        value = {"key": "val"}
        mock = AsyncMock()
        mock.get.return_value = json.dumps(value)
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        result = await cache_get("present")
        assert result == value
        stats = cache_stats()
        assert stats["hits"] >= 1

    async def test_returns_none_on_connection_error(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.get.side_effect = ConnectionError("timeout")
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_get("err") is None


# ── cache_set ─────────────────────────────────────────────────────


class TestCacheSet:
    async def test_returns_false_when_redis_unavailable(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", False)
        assert await cache_set("k", "v") is False

    async def test_sets_value_successfully(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.setex = AsyncMock(return_value=True)
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_set("k", {"data": 42}) is True
        mock.setex.assert_called_once()

    async def test_returns_false_on_timeout(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.setex.side_effect = TimeoutError("timed out")
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_set("k", "v") is False


# ── cache_get_with_stale ──────────────────────────────────────────


class TestCacheGetWithStale:
    async def test_falls_through_to_fetcher_when_redis_down(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", False)
        fetcher = AsyncMock(return_value="fresh")
        result = await cache_get_with_stale("k", 3600, fetcher)
        assert result == "fresh"
        fetcher.assert_called_once()

    async def test_returns_cached_value_on_hit(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.get.return_value = json.dumps("cached")
        mock.ttl.return_value = 300
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        fetcher = AsyncMock()
        result = await cache_get_with_stale("k", 3600, fetcher)
        assert result == "cached"
        fetcher.assert_not_called()

    async def test_deduplicates_concurrent_requests(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.get.return_value = None
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        call_count = 0

        async def slow_fetcher():
            nonlocal call_count
            call_count += 1
            return "result"

        result1 = await cache_get_with_stale("dedup", 3600, slow_fetcher)
        assert result1 == "result"
        assert call_count == 1

    async def test_stale_hit_triggers_background_refresh(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.get.return_value = json.dumps("stale")
        mock.ttl.return_value = 1
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        refresh_called = False

        class _Tracker:
            @staticmethod
            async def fetcher():
                nonlocal refresh_called
                refresh_called = True
                return "fresh"

        result = await cache_get_with_stale("early", 60, _Tracker.fetcher)
        assert result == "stale"

    async def test_in_flight_cleared_after_fetch(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.get.return_value = None
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        await cache_get_with_stale("clear_test", 3600, AsyncMock(return_value="ok"))
        from app.core.cache import _in_flight

        assert "clear_test" not in _in_flight


# ── cache_delete ──────────────────────────────────────────────────


class TestCacheDelete:
    async def test_returns_false_when_redis_unavailable(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", False)
        assert await cache_delete("k") is False

    async def test_deletes_existing_key(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.delete.return_value = 1
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_delete("k") is True

    async def test_returns_false_for_missing_key(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.delete.return_value = 0
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_delete("k") is False


# ── cache_delete_pattern ──────────────────────────────────────────


class TestCacheDeletePattern:
    async def test_returns_zero_when_redis_unavailable(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", False)
        assert await cache_delete_pattern("p*") == 0

    async def test_deletes_matching_keys(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.scan.return_value = (0, ["ic:k1", "ic:k2"])
        mock.delete = AsyncMock(return_value=2)
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_delete_pattern("k*") == 2


# ── cache_exists ──────────────────────────────────────────────────


class TestCacheExists:
    async def test_returns_false_when_redis_unavailable(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", False)
        assert await cache_exists("k") is False

    async def test_returns_true_when_key_exists(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.exists.return_value = 1
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_exists("k") is True

    async def test_returns_false_when_key_missing(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.exists.return_value = 0
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_exists("k") is False


# ── cache_ttl ─────────────────────────────────────────────────────


class TestCacheTtl:
    async def test_returns_negative_two_when_redis_unavailable(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", False)
        assert await cache_ttl("k") == -2

    async def test_returns_ttl_for_existing_key(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.ttl.return_value = 300
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_ttl("k") == 300


# ── cache_ping ────────────────────────────────────────────────────


class TestCachePing:
    async def test_returns_false_when_redis_unavailable_and_reconnect_fails(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._redis", None)
        monkeypatch.setattr("app.core.cache._available", False)

        result = await cache_ping()
        assert result is False

    async def test_pings_successfully(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.ping = AsyncMock(return_value=True)
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        assert await cache_ping() is True


# ── cache_health ──────────────────────────────────────────────────


class TestCacheHealth:
    async def test_returns_unavailable_when_no_redis(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", False)
        health = await cache_health()
        assert health["available"] is False

    async def test_returns_info_when_redis_available(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.info = AsyncMock(
            return_value={
                "redis_version": "7.2",
                "used_memory_human": "1.5M",
                "connected_clients": 5,
                "uptime_in_seconds": 3600,
                "db0": {"keys": 42},
            }
        )
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        health = await cache_health()
        assert health["available"] is True
        assert health["version"] == "7.2"
        assert health["total_keys"] == 42

    async def test_graceful_on_info_error(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        mock = AsyncMock()
        mock.info = AsyncMock(side_effect=ConnectionError("broken"))
        monkeypatch.setattr("app.core.cache._redis", mock)
        monkeypatch.setattr("app.core.cache._available", True)

        health = await cache_health()
        assert health["available"] is True


# ── cache_stats ───────────────────────────────────────────────────


class TestCacheStats:
    def test_returns_defaults_when_no_activity(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        stats = cache_stats()
        assert stats["available"] is False
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 0.0

    def test_computes_hit_rate(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", True)
        monkeypatch.setattr("app.core.cache._hits", 80)
        monkeypatch.setattr("app.core.cache._misses", 20)
        stats = cache_stats()
        assert stats["hit_rate_percent"] == 80.0


# ── Graceful degradation ──────────────────────────────────────────


class TestGracefulDegradation:
    async def test_all_ops_return_safe_defaults_when_redis_down(self, monkeypatch):
        _reset_cache_globals(monkeypatch)
        monkeypatch.setattr("app.core.cache._available", False)
        monkeypatch.setattr("app.core.cache._redis", None)

        assert await cache_get("k") is None
        assert await cache_set("k", "v") is False
        assert await cache_delete("k") is False
        assert await cache_delete_pattern("p*") == 0
        assert await cache_exists("k") is False
        assert await cache_ttl("k") == -2

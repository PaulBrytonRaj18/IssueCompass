"""GitHub service tests — require network access to GitHub API."""
import asyncio

import pytest
from app.services.github_service import (
    fetch_live_issues_for_user,
)


@pytest.mark.skip(reason="Requires network access to GitHub API")
@pytest.mark.asyncio
async def test_search_issues_global_returns_dict():
    pass


@pytest.mark.skip(reason="Requires network access to GitHub API")
@pytest.mark.asyncio
async def test_fetch_user_not_found():
    pass


class TestFetchLiveIssuesForUser:
    """Tests for the new live-fetch function."""

    def test_empty_skill_json_returns_empty_list(self):
        result = asyncio.get_event_loop().run_until_complete(
            fetch_live_issues_for_user({})
        )
        assert result == []

    def test_query_count_capped_at_max_queries(self, monkeypatch):
        call_count = {"n": 0}

        async def fake_search(q, per_page=15, page=1):
            call_count["n"] += 1
            return {"items": []}

        monkeypatch.setattr(
            "app.services.github_service.search_issues_free_text",
            fake_search,
        )

        skill_json = {
            "languages": {"python": 0.4, "typescript": 0.3, "rust": 0.2, "go": 0.1},
            "topics": ["api", "web"],
            "top_skills": [],
        }
        asyncio.get_event_loop().run_until_complete(
            fetch_live_issues_for_user(skill_json, max_queries=6)
        )
        assert call_count["n"] <= 6

    def test_deduplication_by_github_id(self, monkeypatch):
        duplicate_issue = {
            "id": 9999,
            "title": "Duplicate",
            "repository": {"language": "Python", "topics": []},
        }

        async def fake_search(q, per_page=15, page=1):
            return {"items": [duplicate_issue]}

        monkeypatch.setattr(
            "app.services.github_service.search_issues_free_text",
            fake_search,
        )

        skill_json = {"languages": {"python": 0.8}, "topics": [], "top_skills": []}
        result = asyncio.get_event_loop().run_until_complete(
            fetch_live_issues_for_user(skill_json)
        )
        ids = [r["id"] for r in result]
        assert ids.count(9999) == 1

    def test_low_rate_limit_skips_fetch(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.github_service._gh_rate_remaining",
            20,
        )
        search_mock = []

        async def fake_search(q, per_page=15, page=1):
            search_mock.append(True)
            return {"items": []}

        monkeypatch.setattr(
            "app.services.github_service.search_issues_free_text",
            fake_search,
        )

        skill_json = {"languages": {"python": 1.0}, "topics": [], "top_skills": []}
        result = asyncio.get_event_loop().run_until_complete(
            fetch_live_issues_for_user(skill_json)
        )
        assert result == []
        assert len(search_mock) == 0

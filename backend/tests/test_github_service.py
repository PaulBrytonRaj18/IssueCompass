"""GitHub service tests — require network access to GitHub API."""
import pytest


@pytest.mark.skip(reason="Requires network access to GitHub API")
@pytest.mark.asyncio
async def test_search_issues_global_returns_dict():
    pass


@pytest.mark.skip(reason="Requires network access to GitHub API")
@pytest.mark.asyncio
async def test_fetch_user_not_found():
    pass

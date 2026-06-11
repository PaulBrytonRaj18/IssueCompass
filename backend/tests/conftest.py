import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Set required env vars before any app imports
os.environ["GITHUB_TOKEN"] = "test_github_token"
os.environ["OAUTH_GITHUB_CLIENT_ID"] = "test_client_id"
os.environ["OAUTH_GITHUB_CLIENT_SECRET"] = "test_client_secret"
os.environ["SECRET_KEY"] = "test_secret_key_not_default"
os.environ["DATABASE_URL"] = "postgresql://test_user:test_pass@localhost:59999/test_issuecompass"
os.environ["AI_ENABLED"] = "false"
os.environ["GROQ_API_KEY"] = ""
os.environ["EMBEDDINGS_ENABLED"] = "false"
os.environ["JINA_API_KEY"] = ""
os.environ["METRICS_API_KEY"] = ""
os.environ["REDIS_URL"] = "memory://"

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


# ─── Shared helper factories ─────────────────────────────────────────

def make_repo(**kwargs: Any) -> MagicMock:
    defaults: dict[str, Any] = dict(
        id=1,
        github_id=1,
        full_name="owner/repo",
        name="repo",
        owner_login="owner",
        html_url="https://github.com/owner/repo",
        stars=100,
        forks=10,
        primary_language="python",
        topics=[],
        is_archived=False,
        last_indexed=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return MagicMock(spec="app.models.models.Repository", **defaults)


def make_issue(**kwargs: Any) -> MagicMock:
    defaults: dict[str, Any] = dict(
        id=1,
        github_id=100,
        number=1,
        title="Test issue",
        body="Fix the bug",
        html_url="https://github.com/owner/repo/issues/1",
        state="open",
        labels=[],
        is_good_first_issue=False,
        is_help_wanted=False,
        comments=5,
        created_at=datetime.now(timezone.utc),
        required_skills={"categories": {"backend": ["python"]}, "labels": []},
    )
    defaults.update(kwargs)
    return MagicMock(spec="app.models.models.Issue", **defaults)


def make_mock_user(user_id: int = 1) -> MagicMock:
    from app.models.models import User
    user = MagicMock(spec=User)
    user.id = user_id
    user.github_id = 12345
    user.github_username = "testuser"
    user.github_avatar_url = "https://avatars.githubusercontent.com/u/12345"
    user.github_name = "Test User"
    user.github_bio = "A test user"
    user.github_location = None
    user.github_blog = None
    user.email = "test@example.com"
    user.public_repos = 10
    user.followers = 5
    user.skill_json = None
    user.skill_vector = None
    user.skill_last_updated = None
    user.created_at = datetime(2025, 1, 1)
    user.last_login = None
    user.saved_issues = []
    return user


def make_mock_session() -> AsyncMock:
    session = AsyncMock()

    async def execute_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
        result = MagicMock()
        result.scalar_one_or_none.return_value = make_mock_user()
        result.scalar.return_value = 0
        result.fetchall.return_value = []
        return result

    session.execute = AsyncMock(side_effect=execute_side_effect)
    session.add = MagicMock()
    session.commit = AsyncMock(return_value=None)
    session.refresh = AsyncMock(side_effect=lambda obj: (
        setattr(obj, "id", 1) or setattr(obj, "created_at", datetime(2025, 1, 1))
    ))
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ─── Shared fixtures ────────────────────────────────────────────────

@pytest.fixture
def mock_repo() -> MagicMock:
    return make_repo()


@pytest.fixture
def mock_issue() -> MagicMock:
    return make_issue()


@pytest.fixture
def mock_user() -> MagicMock:
    return make_mock_user()


@pytest.fixture
def mock_session() -> AsyncMock:
    return make_mock_session()


@pytest.fixture
def auth_token() -> str:
    from app.routes.auth import create_access_token
    return create_access_token({"sub": "1"})


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}

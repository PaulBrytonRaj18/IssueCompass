from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ─── Auth Schemas ────────────────────────────────────────────

class GitHubUserData(BaseModel):
    github_id: int
    github_username: str
    github_avatar_url: Optional[str] = None
    github_name: Optional[str] = None
    github_bio: Optional[str] = None
    email: Optional[str] = None
    public_repos: int = 0
    followers: int = 0


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserPublic"


# ─── User Schemas ────────────────────────────────────────────

class UserPublic(BaseModel):
    id: int
    github_username: str
    github_avatar_url: Optional[str] = None
    github_name: Optional[str] = None
    github_bio: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    skill_json: Optional[Dict[str, Any]] = None
    skill_last_updated: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SkillFingerprint(BaseModel):
    languages: Dict[str, float]  # language -> confidence 0-1
    topics: List[str]
    categories: Dict[str, List[str]]  # "frontend", "backend", "devops", etc.
    experience_level: str  # beginner, intermediate, advanced
    top_skills: List[str]
    total_repos: int
    total_stars_received: int


# ─── Repository Schemas ──────────────────────────────────────

class RepositoryPublic(BaseModel):
    id: int
    full_name: str
    name: str
    description: Optional[str] = None
    owner_login: str
    html_url: str
    stars: int = 0
    primary_language: Optional[str] = None
    topics: Optional[List[str]] = None

    class Config:
        from_attributes = True


# ─── Issue Schemas ───────────────────────────────────────────

class IssuePublic(BaseModel):
    id: int
    github_id: int
    number: int
    title: str
    body: Optional[str] = None
    html_url: str
    state: str
    labels: Optional[List[str]] = None
    is_good_first_issue: bool = False
    is_help_wanted: bool = False
    required_skills: Optional[Dict[str, Any]] = None
    complexity_score: float = 0.5
    comments: int = 0
    created_at: Optional[datetime] = None
    repository: Optional[RepositoryPublic] = None

    class Config:
        from_attributes = True


class MatchedIssue(BaseModel):
    issue: IssuePublic
    match_score: float
    matching_skills: List[str]
    why_matched: str


class IssueMatchResponse(BaseModel):
    matches: List[MatchedIssue]
    total: int
    user_skills: Optional[SkillFingerprint] = None


# ─── Stats Schemas ───────────────────────────────────────────

class PlatformStats(BaseModel):
    total_users: int
    total_issues_indexed: int
    total_repos_indexed: int
    total_matches_made: int


TokenResponse.model_rebuild()

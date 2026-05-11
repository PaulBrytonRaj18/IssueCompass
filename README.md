# OpenIssue

**Match open-source contributors to issues they can actually solve.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)

---

## The Problem

Developers want to contribute to open source but face a discovery gap:

- **Contributors** browse GitHub aimlessly, wasting hours finding issues matching their skill set
- **Maintainers** tag issues as "good first issue" but attract contributors without the right skills
- **Existing tools** (GitHub Explore, goodfirstissue.dev) are generic lists — zero personalization, zero intelligence

## The Solution

OpenIssue analyzes your **actual GitHub activity** to build a personal skill fingerprint, then uses **pgvector semantic similarity search** to match you with open issues across thousands of repositories that align with your demonstrated abilities.

```
GitHub Login  →  Fetch repos & activity  →  Build skill vector  →  Semantic match  →  Personalized feed
```

---

## Architecture

```
┌──────────┐     GitHub OAuth     ┌──────────────┐     GitHub API     ┌──────────┐
│  Next.js  │ ◄──────────────────► │   FastAPI     │ ◄───────────────► │  GitHub  │
│  Frontend │     JWT (jose)      │   Backend     │    httpx + PAT    │   API    │
│  :3000    │                     │   :8000       │                   │          │
└────┬─────┘                     └──────┬────────┘                   └──────────┘
     │                                  │
     │  Axios API calls                  │  SQLAlchemy async
     │  (Bearer token)                   │  (asyncpg)
     ▼                                  ▼
┌──────────┐                     ┌──────────────┐
│  NextAuth │                     │  PostgreSQL   │
│  Session  │                     │  + pgvector   │
└──────────┘                     │  + Redis      │
                                 └──────────────┘
```

---

## Features

- **GitHub OAuth login** — One-click authentication, no passwords
- **Skill Fingerprint** — Auto-generated from your public repos: languages, topics, categories, experience level
- **Vector Matching** — pgvector cosine similarity between your skills and issue requirements
- **Personalized Feed** — Filter by language and label type (good first issue, help wanted)
- **Why Matched** — Human-readable explanations for every recommendation
- **Issue Indexing** — Background pipeline fetches issues from GitHub across Python, JS, TS, Go, Rust
- **Bookmarking** — Save issues for later, track your contribution pipeline
- **Profile Page** — Full skill visualization with radar charts, language bars, and category breakdown
- **Rate Limiting** — 60 req/min per user, JWT-based identification
- **Dark Theme** — Clean, modern UI built with Tailwind CSS

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, NextAuth.js |
| Backend | FastAPI, Python 3.12, Uvicorn, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| Auth | GitHub OAuth + JWT (HS256, python-jose) |
| Matching | NumPy cosine similarity on 128-dim vectors |
| CI | GitHub Actions (ruff, mypy, pytest, lint) |
| Deployment | Docker Compose |

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- A [GitHub OAuth App](https://github.com/settings/applications/new) (callback URL: `http://localhost:3000/api/auth/callback/github`)
- A [GitHub Personal Access Token](https://github.com/settings/tokens) (scopes: `public_repo`, `read:user`)

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/openissue.git
cd openissue
cp .env.example .env
```

Fill in your `.env` with the values from GitHub:

```env
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_TOKEN=your_personal_access_token
NEXTAUTH_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

### 2. Run with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Manual Setup (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database:**
```bash
# Requires PostgreSQL with pgvector
psql -U postgres -c "CREATE DATABASE openissue;"
psql -U postgres -d openissue -c "CREATE EXTENSION vector;"
```

---

## API Reference

All endpoints are prefixed with `/api/v1`. Authentication via `Authorization: Bearer <token>` header.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/github/callback` | — | Exchange GitHub OAuth data for a JWT |
| `GET` | `/auth/me` | Bearer | Get current user profile |
| `POST` | `/auth/refresh` | Bearer | Refresh the access token |

### GitHub

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/github/analyze/{username}` | Bearer | Build skill fingerprint from GitHub repos |
| `GET` | `/github/user/{username}` | — | Proxy a GitHub user's public profile |
| `GET` | `/github/fingerprint` | Bearer | Get your stored skill fingerprint |

### Issues

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/issues/matches` | Bearer | Get personalized issue matches |
| `POST` | `/issues/index` | — | Trigger background issue indexing |
| `POST` | `/issues/save/{issue_id}` | Bearer | Bookmark an issue |
| `GET` | `/issues/saved` | Bearer | List saved issues |
| `GET` | `/issues/stats` | — | Platform statistics |

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | App info |
| `GET` | `/health` | Health check |

---

## How the Matching Works

### 1. Skill Fingerprint

When you run `POST /github/analyze/{username}`, the backend:

1. Fetches all your public repos from GitHub
2. Extracts languages, topics, and categories using a skill taxonomy (7 categories: frontend, backend, database, devops, AI/ML, mobile, systems)
3. Normalizes language scores to 0-1
4. Estimates experience level from repo count
5. Converts everything into a **128-dimensional vector** using deterministic hashing

### 2. Issue Indexing

`POST /issues/index` triggers a background task that:

1. Searches GitHub for issues tagged `good first issue` and `help wanted` across Python, JavaScript, TypeScript, Go, and Rust
2. Extracts required skills from issue text (title + body + labels)
3. Converts issue text to a 128-dim vector using the same taxonomy
4. Bulk-upserts into PostgreSQL with `ON CONFLICT DO NOTHING`

### 3. Semantic Matching

`GET /issues/matches` computes:

1. **Cosine similarity** between your skill vector and each issue vector
2. **Keyword fallback** for issues without vectors
3. **Explain match** — identifies overlapping skills and classifies strength (Strong > 0.8, Good > 0.5, Partial)
4. Results sorted by score descending, with pagination

---

## Project Structure

```
openissue/
├── backend/                        # FastAPI application
│   ├── app/
│   │   ├── core/                   # Config, DB engine, session
│   │   │   ├── config.py           # Pydantic Settings (env vars)
│   │   │   └── database.py         # AsyncSession, engine, init_db
│   │   ├── models/models.py        # User, Repository, Issue, SavedIssue
│   │   ├── schemas/schemas.py      # Pydantic request/response schemas
│   │   ├── routes/                 # Route handlers
│   │   │   ├── auth.py             # JWT auth, get_me, refresh
│   │   │   ├── github.py           # Analyze, fingerprint, user proxy
│   │   │   └── issues.py           # Matches, index, save, stats
│   │   └── services/               # Business logic
│   │       ├── github_service.py   # httpx GitHub API client
│   │       ├── skill_service.py    # Fingerprint + vector building
│   │       └── matching_service.py # Cosine similarity + scoring
│   ├── tests/                      # pytest test suite
│   ├── main.py                     # FastAPI app entry point
│   └── requirements.txt
├── frontend/                       # Next.js application
│   └── src/
│       ├── app/                    # App Router pages
│       │   ├── page.tsx            # Landing page
│       │   ├── dashboard/page.tsx  # Matches feed
│       │   ├── profile/page.tsx    # Skill fingerprint view
│       │   ├── saved/page.tsx      # Bookmarked issues
│       │   └── api/auth/           # NextAuth route handler
│       ├── components/             # Reusable UI
│       │   ├── Navbar.tsx
│       │   ├── IssueCard.tsx
│       │   ├── SkillFingerprint.tsx
│       │   ├── Spinner.tsx
│       │   └── EmptyState.tsx
│       ├── lib/                    # API client, types, helpers
│       └── styles/globals.css      # Tailwind + dark theme
├── docker-compose.yml              # 4 services: db, redis, backend, frontend
├── .env.example                    # Environment variable template
└── pyproject.toml                  # Ruff + pytest config
```

---

## Database Tables

| Table | Purpose | Key Columns |
|---|---|---|
| `users` | Developer profiles + skill data | `github_id`, `skill_json`, `skill_vector` (Vector 128) |
| `repositories` | Indexed GitHub repos | `full_name`, `stars`, `primary_language`, `topics` |
| `issues` | Indexed issues with skill vectors | `title`, `labels`, `required_skills`, `skill_vector` (Vector 128) |
| `saved_issues` | User bookmarks | `user_id`, `issue_id`, `status` |

---

## Testing

```bash
# Backend tests
cd backend && source venv/bin/activate
pytest -v

# Frontend lint + type check
cd frontend
npm run lint
npx tsc --noEmit
```

---

## Roadmap

- Email digest of new matched issues
- Maintainer dashboard with analytics and promoted placement
- Browser extension (GitHub sidebar integration)
- CLI tool for terminal-based matching
- Slack/Discord bot for issue notifications
- AI-powered skill extraction via LLM
- Contribution streak tracking and gamification

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines. All contributions welcome — features, bug fixes, tests, docs.

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Paul Bryton Raj

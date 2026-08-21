# IssueCompass — Product Requirements Document

> **Version:** 2.0
> **Date:** August 21, 2026
> **Status:** Active Development
> **Repository:** [github.com/PaulBrytonRaj18/IssueCompass](https://github.com/PaulBrytonRaj18/IssueCompass)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Product Vision](#3-product-vision)
4. [Target Users](#4-target-users)
5. [User Personas](#5-user-personas)
6. [User Pain Points](#6-user-pain-points)
7. [Product Goals](#7-product-goals)
8. [Non-Goals](#8-non-goals)
9. [Core User Journey](#9-core-user-journey)
10. [Current Implementation Status](#10-current-implementation-status)
11. [Detailed Feature Requirements](#11-detailed-feature-requirements)
12. [MVP Scope](#12-mvp-scope)
13. [Development Phases](#13-development-phases)
14. [Open Source DNA](#14-open-source-dna)
15. [Project Fit Score](#15-project-fit-score)
16. [Issue Recommendation Engine](#16-issue-recommendation-engine)
17. [Contribution Journey](#17-contribution-journey)
18. [Readiness Evaluation](#18-readiness-evaluation)
19. [Open Source Level System](#19-open-source-level-system)
20. [AI Architecture](#20-ai-architecture)
21. [GitHub Data Architecture](#21-github-data-architecture)
22. [System Architecture](#22-system-architecture)
23. [Database Schema](#23-database-schema)
24. [API Requirements](#24-api-requirements)
25. [Recommendation Algorithm](#25-recommendation-algorithm)
26. [AI vs Deterministic Logic](#26-ai-vs-deterministic-logic)
27. [Cost Optimization Strategy](#27-cost-optimization-strategy)
28. [Trust, Safety and Transparency](#28-trust-safety-and-transparency)
29. [Competitive Analysis](#29-competitive-analysis)
30. [Key Differentiators](#30-key-differentiators)
31. [UX/UI Requirements](#31-uxui-requirements)
32. [Dashboard Structure](#32-dashboard-structure)
33. [Success Metrics](#33-success-metrics)
34. [Risks and Mitigations](#34-risks-and-mitigations)
35. [MVP Acceptance Criteria](#35-mvp-acceptance-criteria)
36. [Future Opportunities](#36-future-opportunities)

---

## 1. Executive Summary

IssueCompass is an **AI-powered Open Source Contribution Compass** that helps developers discover the right open-source projects, identify suitable contribution opportunities, prepare for those contributions, and progressively become stronger open-source contributors.

The product answers one core question:

> **"What should I contribute to next, and why is it the right contribution for me?"**

### Current State (v1.0)

IssueCompass has a **production-ready technical foundation** covering:

- GitHub OAuth authentication
- AI-powered skill fingerprinting (Groq LLM + Jina embeddings)
- 128-dimensional vector similarity search (pgvector)
- 12-factor contribution scoring engine
- Hybrid matching (PostgreSQL + live GitHub API)
- Smart search with NLP query parsing
- Background issue indexing (ARQ cron)
- Full CI/CD pipeline (7-job GitHub Actions)
- Docker Compose + Render deployment

**What exists today:** A smart issue matcher — "Here are issues that match your skills."

**What needs to be built:** A contribution journey platform — "Here is your next step, why it's right for you, and how to prepare."

### Gap Summary

| Area | Coverage | Priority |
|------|----------|----------|
| Authentication & User Profile | ✅ 90% | — |
| Skill Fingerprinting | ✅ 80% | — |
| Issue Matching & Scoring | ✅ 75% | — |
| Repository Discovery | ❌ 0% | P0 |
| Readiness Evaluation | ❌ 0% | P0 |
| Preparation Plans | ❌ 0% | P0 |
| Contribution Journey | ❌ 0% | P0 |
| Open Source Level | ❌ 0% | P1 |
| Dashboard (Full) | ⚠️ 30% | P0 |
| Notifications | ❌ 0% | P2 |

---

## 2. Problem Statement

Many developers, especially students and developers new to open source, want to contribute but struggle with:

| Pain Point | Description |
|------------|-------------|
| Finding relevant projects | GitHub provides enormous information but no personalized guidance |
| Assessing readiness | "Am I good enough for this issue?" |
| Finding matching issues | Filtering through thousands of issues to find the right ones |
| Difficulty assessment | "Is this beginner, intermediate, or advanced?" |
| Maintainer signals | "Is this project actively maintained? Will my PR be reviewed?" |
| Competition awareness | "10 people are already working on this — should I bother?" |
| Learning gaps | "What do I need to learn before attempting this?" |
| Progression | "I fixed a typo — what should I do next?" |
| Portfolio building | "Which contributions will actually build my GitHub profile?" |

GitHub provides the data. IssueCompass provides the **intelligence layer** between the developer and the open-source ecosystem.

---

## 3. Product Vision

### Transform

```
Developer → GitHub Issue
```

### Into

```
Developer → Profile → Open Source Fit → Project → Issue → Preparation → Contribution → PR → Next Contribution
```

### Product Principles

| # | Principle | Description |
|---|-----------|-------------|
| 1 | Personalization over volume | Recommend 5 perfect matches, not 500 mediocre ones |
| 2 | Meaningful contribution over easy contribution | Guide toward growth, not just "good first issue" labels |
| 3 | Explainability over black-box | Every recommendation comes with "because..." |
| 4 | Progression over isolated tasks | Build a journey, not a list |
| 5 | Real data over fabricated insights | GitHub API data + AI analysis, never hallucinated |
| 6 | Low-cost AI usage | LLM for reasoning, algorithms for everything else |
| 7 | User control over automation | Suggest, don't auto-submit |
| 8 | Help users become contributors | Not just issue hunters |

---

## 4. Target Users

| # | User Type | Description | Key Need |
|---|-----------|-------------|----------|
| 1 | **Students** | Want first open-source contribution | Guided entry point |
| 2 | **GSoC Prep** | Preparing for Google Summer of Code | Project discovery + fit scoring |
| 3 | **Junior Devs** | Building credible GitHub portfolios | Progression + portfolio value |
| 4 | **Career Switchers** | Contributing outside own projects | Skill transfer discovery |
| 5 | **Experienced Contributors** | Want better project/issue discovery | Personalized curation |

---

## 5. User Personas

### Persona 1: Priya (Student)

> "I know Python and a little React. I want to contribute to open source but every project looks overwhelming."

**Needs:** Beginner-friendly issues, skill-matched projects, preparation steps, confidence building.

### Persona 2: Marcus (GSoC Applicant)

> "I need to find 3-5 projects I can contribute to before GSoC applications open. I need to demonstrate meaningful contributions."

**Needs:** Project fit scoring, contribution journey tracking, portfolio value assessment.

### Persona 3: Sarah (Junior Developer)

> "I've made a few typo fixes. I want to do real bug fixes but I don't know what I'm ready for."

**Needs:** Readiness evaluation, difficulty assessment, progression guidance.

---

## 6. User Pain Points

| # | Pain Point | Current Solution | Gap |
|---|-----------|------------------|-----|
| 1 | Finding projects relevant to skills | ✅ Skill fingerprint + matching | Need repository-level discovery |
| 2 | Understanding readiness | ❌ Not built | Need readiness evaluation |
| 3 | Finding matching issues | ✅ Hybrid DB + GitHub matching | Need preparation plans |
| 4 | Difficulty assessment | ⚠️ Complexity score exists | Need clearer difficulty labels in UI |
| 5 | Maintainer responsiveness | ❌ Not measured | Need maintainer signal scoring |
| 6 | Avoiding competitive issues | ❌ Not measured | Need competition analysis |
| 7 | Knowing what to learn | ❌ Not built | Need prerequisite detection |
| 8 | Progression after contribution | ❌ Not built | Need journey tracking |
| 9 | Portfolio value | ❌ Not assessed | Need portfolio scoring |

---

## 7. Product Goals

| # | Goal | Metric | Current Status |
|---|------|--------|----------------|
| G1 | Help developers find their first contribution | Time to first match < 60 seconds | ✅ Achieved |
| G2 | Provide personalized recommendations | Match relevance > 70% user satisfaction | ✅ Backend ready |
| G3 | Guide contribution progression | Users complete 2+ contributions in 30 days | ❌ Not measurable |
| G4 | Explain recommendation reasoning | Every match has "why_matched" | ✅ Achieved |
| G5 | Minimize AI costs | < $0.01 per user session | ✅ Achieved (cache-first) |
| G6 | Support contribution journey | Track PR status + suggest next step | ❌ Not built |
| G7 | Evaluate user readiness | "You're ready" / "Learn X first" | ❌ Not built |

---

## 8. Non-Goals

The initial product should NOT:

| # | Non-Goal | Reason |
|---|----------|--------|
| NG1 | Replace GitHub | Complement, not compete |
| NG2 | Auto-submit PRs | User control is a principle |
| NG3 | Guarantee PR acceptance | We can't control maintainers |
| NG4 | Guarantee GSoC selection | We can guide, not guarantee |
| NG5 | Predict maintainer behavior | Present signals, not certainties |
| NG6 | Generic AI coding assistant | Stay focused on OSS contribution |
| NG7 | Another issue search engine | Differentiate with personalization |
| NG8 | Excessive gamification | Levels represent capability, not points |

---

## 9. Core User Journey

### Current Journey (v1.0)

```
Sign In → Analyze Profile → View Matches → Search Issues → Save Issues
```

### Target Journey (v2.0)

```
Sign In
  ↓
Analyze Profile → Build Open Source DNA
  ↓
Discover Projects → See Project Fit Scores
  ↓
Evaluate Readiness → "You're ready" or "Learn X first"
  ↓
View Recommended Issues → See Why + Preparation Plan
  ↓
Attempt Issue → Track Progress
  ↓
Submit PR → Track Status
  ↓
Contribution Merged → Update Level
  ↓
See "Next Move" → Repeat
```

### Journey States

| State | Description | Trigger |
|-------|-------------|---------|
| `discover` | Browsing recommended projects | First login |
| `evaluate` | Assessing fit for a specific project | Clicking a project |
| `prepare` | Following preparation plan | Choosing an issue |
| `attempt` | Working on the issue | Starting work |
| `submitted` | PR submitted | PR link provided |
| `review` | PR under review | PR status check |
| `merged` | Contribution accepted | PR merged (GitHub webhook) |
| `learn` | Reflecting on contribution | Post-merge |
| `next` | Ready for next contribution | After learning state |

---

## 10. Current Implementation Status

### What Exists Today

#### Authentication ✅
- GitHub OAuth via NextAuth v4
- JWT tokens (HS256, 7-day expiry)
- HttpOnly cookies + Bearer token dual auth
- CSRF protection on OAuth flow

**Files:** `backend/app/routes/auth.py`, `frontend/src/app/api/auth/`, `frontend/src/middleware.ts`

#### Open Source DNA (Partial) ⚠️
- Languages (weighted by repo count)
- Topics (extracted from repos)
- Categories (frontend, backend, database, devops, ai_ml, mobile, systems)
- Experience level (beginner/intermediate/advanced by repo count)
- Top skills (AI-powered via Groq LLM)
- 128-dimensional skill vector (Jina embeddings)

**Files:** `backend/app/services/skill_service.py`, `backend/app/services/ai_service.py`

**Missing:** Contribution history, PR analysis, issue authorship, learning goals, preferred difficulty.

#### Issue Matching ✅
- pgvector cosine similarity search
- 12-factor weighted scoring
- Hybrid: DB issues + live GitHub API results
- Deduplication and re-ranking
- Language, label, difficulty filters

**Files:** `backend/app/services/matching_service.py`, `backend/app/services/scoring_service.py`

#### Smart Search ✅
- Natural language query parsing (AI + regex fallback)
- Language detection, difficulty detection, label detection
- Semantic scoring with vector similarity
- GitHub fallback for empty DB results

**Files:** `backend/app/services/search_service.py`, `backend/app/routes/issues.py`

#### Background Indexing ✅
- ARQ worker with cron jobs
- Indexes issues every 6 hours
- Cleans up stale issues daily
- Prioritizes languages based on user skill data

**Files:** `backend/app/worker.py`

#### Infrastructure ✅
- Docker Compose (5 services)
- Render deployment (3 services)
- GitHub Actions CI/CD (7-job pipeline)
- Structured JSON logging
- Sentry error tracking
- Rate limiting (SlowAPI)
- Redis caching with stampede protection

### What Does NOT Exist

| Feature | Status | Priority |
|---------|--------|----------|
| Repository recommendation | Not built | P0 |
| Project-level fit score | Not built | P0 |
| Readiness evaluation | Not built | P0 |
| Preparation plans | Not built | P0 |
| Contribution journey tracking | Not built | P0 |
| "Next Move" dashboard widget | Not built | P0 |
| Open Source Level system | Not built | P1 |
| Maintainer responsiveness score | Not built | P1 |
| Competition analysis | Not built | P1 |
| PR status monitoring | Not built | P1 |
| Notification system | Not built | P2 |
| Dark mode toggle | Not built | P2 |
| Mobile optimization | Not built | P2 |

---

## 11. Detailed Feature Requirements

### Feature 1: Repository Discovery

**User Story:**
> As a developer, I want to see repositories recommended for me so I can find the right project to contribute to.

**Functional Requirements:**
1. Recommend repositories based on user's skill fingerprint
2. Show project-level fit score (0-100%)
3. Display: name, description, tech stack, activity level, contributors, issue count
4. Show maintainer signals (last commit, average PR merge time)
5. Show competition level (active contributors, recent PRs)
6. Explain why the project is recommended

**Inputs:** User skill_vector, skill_json
**Outputs:** Ranked list of repositories with fit scores and explanations

**Edge Cases:**
- User has no skill fingerprint → prompt analysis first
- Repository is archived → exclude from results
- Repository has no open issues → show with low priority

**Dependencies:** GitHub API (repository metadata, contributors, recent activity)

**MVP Priority:** P0 — Critical

**Implementation Notes:**
- Backend: New endpoint `GET /api/v1/repos/recommended`
- Score combines: skill_match (0.40), activity (0.20), contributor_friendliness (0.15), issue_availability (0.15), learning_value (0.10)
- Cache results for 30 minutes
- Use existing `github_service.fetch_user_repos` pattern for data fetching

---

### Feature 2: Readiness Evaluation

**User Story:**
> As a developer, I want to know if I'm ready to tackle a specific issue before I attempt it.

**Functional Requirements:**
1. Analyze issue's required skills vs user's skill fingerprint
2. Identify skill gaps
3. Return readiness status: `ready`, `almost_ready`, `not_ready`
4. List specific skills the user needs to learn
5. Suggest preparation resources

**Inputs:** User skill_json, Issue required_skills, Issue skill_vector
**Outputs:** Readiness assessment with explanation

**Edge Cases:**
- Issue has no skill data → return `unknown` with generic advice
- User has no skill fingerprint → prompt analysis
- Issue requires skills not in any category → mark as `external_prerequisite`

**Dependencies:** Skill fingerprint, Issue required_skills (from `skill_service.extract_required_skills`)

**MVP Priority:** P0 — Critical

**Implementation Notes:**
- Backend: New endpoint `GET /api/v1/issues/{issue_id}/readiness`
- Deterministic: Compare user skill categories against issue skill categories
- Return confidence level alongside readiness status
- AI enhancement (Phase 2): Use Groq to generate personalized readiness explanation

---

### Feature 3: Preparation Plans

**User Story:**
> As a developer, I want a step-by-step plan to prepare for an issue before I start working on it.

**Functional Requirements:**
1. Generate 3-5 step preparation plan per issue
2. Steps include: repository setup, architecture review, related PR review, skill prerequisites
3. Plans adapt based on user's experience level
4. Plans reference actual repository data (CONTRIBUTING.md, README, setup instructions)

**Inputs:** Issue data, Repository data, User experience level
**Outputs:** Ordered preparation steps with links

**Edge Cases:**
- Repository has no CONTRIBUTING.md → generic setup steps
- Repository has no README → skip architecture review step
- User is advanced → skip basic steps

**Dependencies:** GitHub API (README, CONTRIBUTING.md), Repository metadata

**MVP Priority:** P0 — Critical

**Implementation Notes:**
- Backend: New field in issue recommendation response: `preparation_plan`
- Rule-based first (Phase 1): Check CONTRIBUTING.md exists, check setup docs, check recent PRs
- AI-enhanced (Phase 2): Use Groq to generate context-aware preparation steps
- Cache plans per (issue_id, experience_level) for 1 hour

---

### Feature 4: Contribution Journey Tracking

**User Story:**
> As a developer, I want to track my open-source journey from discovery to merged contribution.

**Functional Requirements:**
1. Track journey state per saved issue: `saved → in_progress → submitted → merged`
2. Monitor PR status via GitHub API (opened, closed, merged)
3. Show journey progress on dashboard
4. Record contribution history for level calculation

**Inputs:** User ID, Issue ID, GitHub PR URL
**Outputs:** Journey state, contribution history

**Edge Cases:**
- PR is closed without merge → mark as `closed` (not failed)
- User submits multiple PRs for same issue → track latest
- GitHub API rate limit → queue status check for later

**Dependencies:** GitHub API (pull request status), SavedIssue model

**MVP Priority:** P0 — Critical

**Implementation Notes:**
- Enhance existing `SavedIssue` model with journey state fields
- Add `github_pr_url`, `pr_status`, `pr_merged_at` columns
- Background worker: cron job checks PR status every 2 hours
- Frontend: Journey progress indicator on dashboard

---

### Feature 5: "Next Move" Dashboard Widget

**User Story:**
> As a developer, I want to see my next recommended action prominently on the dashboard.

**Functional Requirements:**
1. Show "YOUR NEXT MOVE" card at top of dashboard
2. Recommend: specific issue, specific project, or preparation step
3. Explain why in 1-2 sentences
4. Show confidence level
5. Handle edge cases: no skills, no matches, in-progress contribution

**Inputs:** User profile, matches, journey state
**Outputs:** Single top recommendation with explanation

**Edge Cases:**
- User has no skill fingerprint → "Analyze your profile first"
- User has in-progress contribution → "Continue working on X"
- No matches found → "Try broadening your filters"
- All good matches are saved → "You've saved all top matches — try a new search"

**Dependencies:** Matches, Journey state, Skill fingerprint

**MVP Priority:** P0 — Critical

**Implementation Notes:**
- Backend: New endpoint `GET /api/v1/recommendations/next-move`
- Logic: Check journey state first (if in-progress → continue), then top match, then suggestion
- Frontend: Prominent card at top of dashboard with CTA button

---

### Feature 6: Open Source Level System

**User Story:**
> As a developer, I want to see my progression as an open-source contributor.

**Functional Requirements:**
1. 5 levels based on contribution capability (not gamification)
2. Levels: Explorer → First Contributor → Active Contributor → Reliable Contributor → Project Contributor
3. Level calculated from: merged PRs, issue types completed, repos contributed to, consistency
4. Show level on profile and dashboard
5. Show what's needed to reach next level

**Inputs:** Contribution history, PR merge data, repository diversity
**Outputs:** Current level, progress to next level, requirements

**Edge Cases:**
- New user with no contributions → Level 1 (Explorer)
- User with only documentation PRs → Level 2 (First Contributor)
- User inactive for 6+ months → maintain level but show "stale" indicator

**Dependencies:** Contribution history (from Feature 4)

**MVP Priority:** P1

**Implementation Notes:**
- Backend: New model `UserLevel` or computed from contribution history
- Calculation: Deterministic formula based on merged PR count, repo diversity, issue complexity
- Frontend: Level badge on profile, progress bar on dashboard

---

### Feature 7: Maintainer Responsiveness Score

**User Story:**
> As a developer, I want to know if a project's maintainers are responsive before I invest time.

**Functional Requirements:**
1. Calculate responsiveness score (0-100) per repository
2. Factors: last commit date, average PR merge time, issue response time, maintainer count
3. Present as signal, not fact: "Estimated: Active maintainers"
4. Cache scores for 6 hours

**Inputs:** Repository metadata, recent commits, PR merge times
**Outputs:** Responsiveness score and description

**Edge Cases:**
- Single-maintainer repo → show "Small team, may be slow"
- No recent activity → "Low activity — PRs may not be reviewed"
- Corporate-backed repo → "Backed by [company], likely responsive"

**Dependencies:** GitHub API (commits, PRs, issues)

**MVP Priority:** P1

---

### Feature 8: Competition Analysis

**User Story:**
> As a developer, I want to know how many people are already working on an issue.

**Functional Requirements:**
1. Count linked PRs on an issue
2. Count active comments from non-maintainers
3. Calculate competition level: low, medium, high
4. Present as signal: "3 other contributors appear active"

**Inputs:** GitHub issue data (linked PRs, comments)
**Outputs:** Competition level and count

**Edge Cases:**
- No linked PRs → "Low competition"
- Multiple abandoned PRs → "Past attempts, may be difficult"
- Issue labeled "stale" → "Possibly abandoned"

**Dependencies:** GitHub API (issue timeline, linked PRs)

**MVP Priority:** P1

---

## 12. MVP Scope

### MVP Features (Phase 1 — Must Have)

| # | Feature | Status | Effort |
|---|---------|--------|--------|
| 1 | GitHub Authentication | ✅ Done | — |
| 2 | GitHub Profile Analysis | ✅ Done | — |
| 3 | Skill Fingerprinting | ✅ Done | — |
| 4 | Issue Matching + Scoring | ✅ Done | — |
| 5 | Repository Discovery | ❌ Not Built | 1-2 weeks |
| 6 | Contribution Fit Score (enhanced) | ⚠️ Partial | 1 week |
| 7 | Readiness Evaluation | ❌ Not Built | 1 week |
| 8 | Preparation Plans | ❌ Not Built | 1 week |
| 9 | "Next Move" Widget | ❌ Not Built | 3-5 days |
| 10 | Contribution Journey Tracking | ❌ Not Built | 1-2 weeks |
| 11 | Explainable Recommendations | ✅ Done | — |
| 12 | Dashboard (full) | ⚠️ Partial | 1-2 weeks |

### MVP NOT Included (Phase 2+)

| Feature | Phase | Reason |
|---------|-------|--------|
| Open Source Level | Phase 2 | Needs journey data first |
| Notifications | Phase 3 | Needs PR tracking first |
| Dark mode | Phase 3 | Nice-to-have |
| Mobile optimization | Phase 3 | Desktop-first for MVP |
| AI preparation plans | Phase 2 | Rule-based first |

---

## 13. Development Phases

### Phase 1: Core Journey (4-6 weeks)

**Goal:** Transform from issue matcher to contribution guide.

| Week | Feature | Deliverable |
|------|---------|-------------|
| 1-2 | Repository Discovery | `/repos/recommended` endpoint + frontend page |
| 2-3 | Readiness Evaluation + Preparation Plans | `/issues/{id}/readiness` endpoint + UI card |
| 3-4 | "Next Move" Widget | Dashboard top card + recommendation logic |
| 4-5 | Contribution Journey Tracking | Enhanced SavedIssue + PR status monitoring |
| 5-6 | Dashboard Redesign | Full dashboard with all new sections |

### Phase 2: Intelligence Layer (3-4 weeks)

**Goal:** Add progression and deeper analysis.

| Week | Feature | Deliverable |
|------|---------|-------------|
| 1-2 | Open Source Level System | Level calculation + profile badge |
| 2-3 | Maintainer Responsiveness Score | Repo scoring + display |
| 3-4 | Competition Analysis | Issue competition signals |
| 4 | AI Preparation Plans | Groq-powered context-aware plans |

### Phase 3: Polish & Scale (3-4 weeks)

**Goal:** Production polish and growth features.

| Week | Feature | Deliverable |
|------|---------|-------------|
| 1-2 | Notification System | Email/webhook for matching issues |
| 2-3 | Mobile Responsive | Full mobile support |
| 3-4 | Dark Mode + UX Polish | Theme toggle, animations, onboarding |

---

## 14. Open Source DNA

### Current Fields (v1.0)

```json
{
  "languages": { "python": 0.45, "javascript": 0.30, "typescript": 0.25 },
  "topics": ["react", "fastapi", "postgresql"],
  "categories": { "frontend": ["react"], "backend": ["python", "fastapi"] },
  "experience_level": "intermediate",
  "top_skills": ["python", "react", "fastapi"],
  "total_repos": 15,
  "total_stars_received": 342
}
```

### Target Fields (v2.0)

```json
{
  "languages": { "python": 0.45, "javascript": 0.30 },
  "topics": ["react", "fastapi"],
  "categories": { "frontend": ["react"], "backend": ["python"] },
  "experience_level": "intermediate",
  "top_skills": ["python", "react", "fastapi"],
  "total_repos": 15,
  "total_stars_received": 342,

  "contribution_history": {
    "total_prs": 12,
    "merged_prs": 8,
    "repos_contributed_to": 5,
    "first_contribution_date": "2025-03-15",
    "last_contribution_date": "2026-08-10",
    "contribution_types": {
      "documentation": 3,
      "bug_fix": 4,
      "feature": 1
    }
  },

  "contribution_capability": {
    "can_handle_docs": true,
    "can_handle_bug_fixes": true,
    "can_handle_features": false,
    "can_handle_refactors": false,
    "comfortable_with": ["python", "react", "sql"],
    "needs_learning": ["typescript-advanced", "testing", "ci-cd"]
  },

  "preferences": {
    "preferred_difficulty": "beginner",
    "preferred_languages": ["python", "javascript"],
    "interests": ["web", "api", "database"],
    "learning_goals": ["learn rust", "contribute to pytorch"]
  }
}
```

### How to Build It

| Field | Source | Method |
|-------|--------|--------|
| contribution_history | GitHub API: `/users/{username}/repos`, `/repos/{owner}/{repo}/pulls` | Deterministic |
| contribution_capability | skill_json + contribution_history | Rule-based inference |
| preferences | User settings (Phase 2) | User input |

---

## 15. Project Fit Score

### Current Scoring (Issue Level)

```python
SCORE_WEIGHTS = {
    "skill_match": 0.50,      # Cosine similarity
    "popularity": 0.15,       # Stars, forks, comments
    "repo_activity": 0.10,    # Last indexed, star threshold
    "interest_match": 0.15,   # Topic/category overlap
    "freshness": 0.10,        # Issue age
}
```

### Target Scoring (Project Level)

```python
PROJECT_SCORE_WEIGHTS = {
    "skill_match": 0.30,           # User languages/topics vs repo
    "activity": 0.20,              # Recent commits, releases, PR merges
    "contributor_friendliness": 0.15,  # CONTRIBUTING.md, good first issue count
    "issue_availability": 0.15,    # Open issues matching user skills
    "learning_value": 0.10,        # New technologies user hasn't used
    "portfolio_value": 0.10,       # Repo popularity, tech stack relevance
}
```

### Score Explanation Format

```
Project: fastapi/fastapi
Fit Score: 87%

✅ Strong Python match (your top language)
✅ Active repository (3 commits this week)
✅ 5 issues match your skill level
✅ Well-documented (CONTRIBUTING.md present)
⚠️ Uses async patterns you haven't explored
⚠️ Moderate contributor competition (12 open PRs)
```

---

## 16. Issue Recommendation Engine

### Current Pipeline

```
1. Parse user filters (language, label, difficulty)
2. Run concurrently:
   a. DB: pgvector cosine similarity (local issues)
   b. GitHub: live search (user's top languages + labels)
3. Deduplicate (DB wins over live)
4. Re-rank with 12-factor scoring
5. Cache for 3 minutes
6. Return paginated results
```

### Target Pipeline (v2.0)

```
1. Get user's Open Source DNA
2. Get user's journey state (in-progress? recently merged?)
3. Determine recommendation mode:
   a. If in-progress → show "continue" recommendation
   b. If recently merged → suggest next difficulty level
   c. If new → show beginner-friendly projects
4. Score repositories against user (Project Fit Score)
5. For top 5 repositories, find matching issues
6. For each issue:
   a. Calculate Issue Match Score
   b. Evaluate Readiness
   c. Generate Preparation Plan
   d. Assess Competition Level
7. Rank combined results
8. Generate "Next Move" recommendation
9. Return with explanations
```

---

## 17. Contribution Journey

### Journey States

| State | Description | Data Needed |
|-------|-------------|-------------|
| `discover` | Browsing projects/issues | — |
| `evaluate` | Assessing a specific issue | Issue data, readiness check |
| `prepare` | Following preparation plan | Plan steps, completion status |
| `attempt` | Working on the issue | Start timestamp |
| `submitted` | PR submitted | GitHub PR URL |
| `review` | PR under review | PR status from GitHub |
| `merged` | Contribution accepted | PR merged timestamp |
| `learn` | Reflecting on contribution | User reflection (optional) |
| `next` | Ready for next contribution | Level recalculation |

### State Transitions

```
discover → evaluate → prepare → attempt → submitted → review → merged → learn → next
                ↑                                    ↓
                └────── (if PR closed) ──────────────┘
                         attempt (retry)
```

### Next Contribution Logic

```python
def recommend_next(contribution_history):
    last_type = contribution_history.last_contribution_type
    merged_count = contribution_history.merged_count

    if merged_count == 0:
        return "Find a good first issue"
    elif last_type == "documentation" and merged_count < 3:
        return "Try a small bug fix"
    elif last_type == "bug_fix" and merged_count < 5:
        return "Try a medium bug fix or small feature"
    elif last_type == "feature":
        return "Try a more complex feature or refactor"
    else:
        return "You're ready for advanced contributions"
```

---

## 18. Readiness Evaluation

### Readiness States

| State | Meaning | Action |
|-------|---------|--------|
| `ready` | User has all required skills | "You're ready! Start working." |
| `almost_ready` | Missing 1-2 skills | "Learn X before starting." |
| `not_ready` | Missing core skills | "You should learn X, Y, Z first." |
| `unknown` | Cannot determine | "Review the issue requirements." |

### Evaluation Algorithm

```python
def evaluate_readiness(user_skills, issue_required_skills):
    user_categories = set(user_skills.get("categories", {}).keys())
    issue_categories = set(issue_required_skills.get("categories", {}).keys())

    covered = user_categories & issue_categories
    missing = issue_categories - user_categories

    coverage = len(covered) / max(len(issue_categories), 1)

    if coverage >= 0.8:
        return "ready", []
    elif coverage >= 0.5:
        return "almost_ready", list(missing)
    else:
        return "not_ready", list(missing)
```

---

## 19. Open Source Level System

### Levels

| Level | Name | Criteria | Badge |
|-------|------|----------|-------|
| 1 | Explorer | No merged PRs yet | 🔍 |
| 2 | First Contributor | 1+ merged PRs | 🌱 |
| 3 | Active Contributor | 5+ merged PRs across 2+ repos | 🌿 |
| 4 | Reliable Contributor | 15+ merged PRs across 3+ repos, includes features | 🌳 |
| 5 | Project Contributor | 30+ merged PRs, 2+ repos with 10+ contributions each | 🏔️ |

### Level Calculation

```python
def calculate_level(merged_prs, repos_contributed, has_features):
    if merged_prs == 0:
        return 1
    elif merged_prs >= 1 and repos_contributed == 1:
        return 2
    elif merged_prs >= 5 and repos_contributed >= 2:
        return 3
    elif merged_prs >= 15 and repos_contributed >= 3 and has_features:
        return 4
    elif merged_prs >= 30 and repos_contributed >= 2:
        return 5
    return max(1, min(4, merged_prs // 5 + 1))
```

---

## 20. AI Architecture

### Current AI Usage

| Task | Model | When | Cost |
|------|-------|------|------|
| Skill analysis | Groq LLaMA 3.3 70B | On profile analysis | Cached 24h |
| Issue analysis | Groq LLaMA 3.3 70B | On indexing | Cached 24h |
| Query parsing | Groq LLaMA 3.3 70B | On smart search | Cached 24h |
| Match explanation | Groq LLaMA 3.3 70B | On match request | Cached 1h |
| Embeddings | Jina v3 (128-dim) | On analysis/indexing | Cached 24h |

### Target AI Usage (v2.0)

| Task | Model | When | Cost |
|------|-------|------|------|
| *(existing)* | *(same)* | *(same)* | *(same)* |
| Readiness explanation | Groq LLaMA 3.3 70B | On readiness request | Cached 1h |
| Preparation plan | Groq LLaMA 3.3 70B | On issue selection | Cached 1h |
| Next move reasoning | Rule-based (no AI) | On dashboard load | Free |
| Level calculation | Rule-based (no AI) | On contribution update | Free |

### AI Cost Budget

| Metric | Target | Current |
|--------|--------|---------|
| LLM calls per user session | < 3 | ~2 |
| Cost per user session | < $0.01 | ~$0.003 |
| Cache hit rate | > 80% | ~70% |
| Embedding cost per analysis | < $0.001 | ~$0.0005 |

---

## 21. GitHub Data Architecture

### Data Sources

| Data | API Endpoint | Frequency | Cache TTL |
|------|-------------|-----------|-----------|
| User profile | `GET /users/{username}` | On login | 1 hour |
| User repos | `GET /users/{username}/repos` | On analysis | 30 min |
| Repo languages | `GET /repos/{owner}/{repo}/languages` | On analysis | 24 hours |
| Repo issues | `GET /repos/{owner}/{repo}/issues` | On indexing | 10 min |
| Repo contributors | `GET /repos/{owner}/{repo}/contributors` | On project view | 6 hours |
| Repo commits | `GET /repos/{owner}/{repo}/commits` | On project view | 6 hours |
| Issue timeline | `GET /repos/{owner}/{repo}/issues/{id}/timeline` | On readiness check | 1 hour |
| Pull requests | `GET /repos/{owner}/{repo}/pulls` | On competition check | 15 min |
| PR status | `GET /repos/{owner}/{repo}/pulls/{id}` | On journey update | 5 min |
| CONTRIBUTING.md | `GET /repos/{owner}/{repo}/contents/CONTRIBUTING.md` | On preparation plan | 24 hours |

### Data Separation

```
1. Data retrieved directly from GitHub (raw)
   → Repos, issues, PRs, commits, contributors

2. Deterministic calculations (computed)
   → Skill match, popularity, freshness, activity, readiness

3. AI-generated analysis (inferred)
   → Skill fingerprint, issue skills, explanations, plans
```

---

## 22. System Architecture

### Current Architecture

```
Browser → Next.js (SSR) → FastAPI (REST API) → PostgreSQL (pgvector)
                           │                       └── Redis (cache)
                           │
                           ├── GitHub REST API
                           ├── Groq Cloud (LLaMA 3.3 70B)
                           └── Jina AI (embeddings v3)
```

### Target Architecture (v2.0)

```
Browser → Next.js (SSR) → FastAPI (REST API) → PostgreSQL (pgvector)
                           │                       └── Redis (cache)
                           │
                           ├── GitHub REST API
                           │   ├── User data (repos, profile)
                           │   ├── Repository data (commits, contributors)
                           │   ├── Issue data (timeline, linked PRs)
                           │   └── PR data (status, reviews)
                           │
                           ├── Groq Cloud (LLaMA 3.3 70B)
                           │   ├── Skill analysis
                           │   ├── Issue analysis
                           │   ├── Readiness explanations
                           │   └── Preparation plans
                           │
                           └── Jina AI (embeddings v3)
                               └── Semantic vectors (128-dim)
```

### New Backend Modules

```
backend/app/
├── services/
│   ├── project_service.py      # NEW: Repository discovery + scoring
│   ├── readiness_service.py    # NEW: Readiness evaluation
│   ├── journey_service.py      # NEW: Contribution journey tracking
│   ├── level_service.py        # NEW: Open Source Level calculation
│   └── notification_service.py # NEW: Notification system (Phase 3)
├── models/
│   └── models.py               # ENHANCED: New columns on SavedIssue
└── routes/
    ├── repos.py                # NEW: Repository endpoints
    ├── recommendations.py      # NEW: Next-move + readiness
    └── journey.py              # NEW: Journey tracking endpoints
```

---

## 23. Database Schema

### Current Schema (4 tables)

```sql
-- users: GitHub profile + skill data
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    github_id BIGINT UNIQUE NOT NULL,
    github_username VARCHAR(100) UNIQUE NOT NULL,
    skill_json JSONB,
    skill_vector vector(128),
    skill_last_updated TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- repositories: Indexed repos
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    github_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(300) UNIQUE NOT NULL,
    stars INTEGER DEFAULT 0,
    topics JSON,
    last_indexed TIMESTAMPTZ,
    -- ... other fields
);

-- issues: Indexed issues with vectors
CREATE TABLE issues (
    id SERIAL PRIMARY KEY,
    github_id BIGINT UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    skill_vector vector(128),
    required_skills JSON,
    complexity_score FLOAT DEFAULT 0.5,
    repository_id INTEGER REFERENCES repositories(id),
    -- ... other fields
);

-- saved_issues: User's saved/bookmarked issues
CREATE TABLE saved_issues (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    issue_id INTEGER REFERENCES issues(id),
    saved_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'saved',
    UNIQUE(user_id, issue_id)
);
```

### Target Schema (v2.0 — Additions)

```sql
-- ENHANCE saved_issues with journey tracking
ALTER TABLE saved_issues ADD COLUMN github_pr_url VARCHAR(500);
ALTER TABLE saved_issues ADD COLUMN pr_status VARCHAR(50);  -- null, open, closed, merged
ALTER TABLE saved_issues ADD COLUMN pr_submitted_at TIMESTAMPTZ;
ALTER TABLE saved_issues ADD COLUMN pr_merged_at TIMESTAMPTZ;
ALTER TABLE saved_issues ADD COLUMN started_at TIMESTAMPTZ;
ALTER TABLE saved_issues ADD COLUMN preparation_completed BOOLEAN DEFAULT FALSE;

-- NEW: user_levels (computed from contribution history)
CREATE TABLE user_levels (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id),
    level INTEGER DEFAULT 1,
    merged_prs INTEGER DEFAULT 0,
    repos_contributed INTEGER DEFAULT 0,
    last_calculated TIMESTAMPTZ DEFAULT NOW()
);

-- NEW: project_recommendations (cached project scores)
CREATE TABLE project_recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    repository_id INTEGER REFERENCES repositories(id),
    fit_score FLOAT NOT NULL,
    score_breakdown JSON,
    explanation TEXT,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, repository_id)
);

-- NEW: preparation_plans (cached per issue + experience level)
CREATE TABLE preparation_plans (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER REFERENCES issues(id),
    experience_level VARCHAR(50) NOT NULL,
    steps JSON NOT NULL,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(issue_id, experience_level)
);
```

---

## 24. API Requirements

### Current Endpoints (21)

| Method | Path | Status |
|--------|------|--------|
| GET | `/` | ✅ Exists |
| GET | `/health` | ✅ Exists |
| GET | `/metrics` | ✅ Exists |
| GET | `/api/v1/auth/state` | ✅ Exists |
| POST | `/api/v1/auth/github/callback` | ✅ Exists |
| GET | `/api/v1/auth/me` | ✅ Exists |
| POST | `/api/v1/auth/refresh` | ✅ Exists |
| POST | `/api/v1/github/analyze/{username}` | ✅ Exists |
| GET | `/api/v1/github/user/{username}` | ✅ Exists |
| GET | `/api/v1/github/fingerprint` | ✅ Exists |
| GET | `/api/v1/issues/matches` | ✅ Exists |
| POST | `/api/v1/issues/index` | ✅ Exists |
| POST | `/api/v1/issues/save/{id}` | ✅ Exists |
| GET | `/api/v1/issues/saved` | ✅ Exists |
| GET | `/api/v1/issues/trending` | ✅ Exists |
| GET | `/api/v1/issues/smart-search` | ✅ Exists |
| GET | `/api/v1/issues/stats` | ✅ Exists |

### New Endpoints (v2.0 — +10)

| Method | Path | Description | Priority |
|--------|------|-------------|----------|
| GET | `/api/v1/repos/recommended` | Project recommendations | P0 |
| GET | `/api/v1/repos/{full_name}` | Repository detail + fit score | P0 |
| GET | `/api/v1/issues/{id}/readiness` | Readiness evaluation | P0 |
| GET | `/api/v1/issues/{id}/preparation` | Preparation plan | P0 |
| GET | `/api/v1/recommendations/next-move` | Top recommendation | P0 |
| PUT | `/api/v1/saved/{id}/journey` | Update journey state | P0 |
| GET | `/api/v1/saved/journey` | Get journey progress | P0 |
| GET | `/api/v1/users/me/level` | Get Open Source Level | P1 |
| GET | `/api/v1/repos/{full_name}/maintainers` | Maintainer signals | P1 |
| GET | `/api/v1/issues/{id}/competition` | Competition analysis | P1 |

---

## 25. Recommendation Algorithm

### Project Recommendation

```python
def score_project(user: User, repo: Repository) -> float:
    # Skill match (0.30)
    skill_score = compute_skill_match(user.skill_json, repo)

    # Activity (0.20)
    activity_score = compute_activity_score(repo)

    # Contributor friendliness (0.15)
    friendliness_score = compute_friendliness_score(repo)

    # Issue availability (0.15)
    availability_score = compute_availability_score(repo, user)

    # Learning value (0.10)
    learning_score = compute_learning_value(user, repo)

    # Portfolio value (0.10)
    portfolio_score = compute_portfolio_value(user, repo)

    return (
        skill_score * 0.30
        + activity_score * 0.20
        + friendliness_score * 0.15
        + availability_score * 0.15
        + learning_score * 0.10
        + portfolio_score * 0.10
    )
```

### Issue Recommendation (Enhanced)

```python
def score_issue_enhanced(user, issue, repo, readiness) -> float:
    # Existing 5 factors
    base_score = current_scoring(user, issue, repo)

    # New factors
    readiness_bonus = 0.10 if readiness == "ready" else 0.0
    competition_penalty = compute_competition_penalty(issue)
    portfolio_bonus = compute_portfolio_bonus(user, issue)

    return base_score + readiness_bonus - competition_penalty + portfolio_bonus
```

### Next Move Selection

```python
def select_next_move(user, journey_state, matches):
    # Priority 1: Continue in-progress contribution
    if journey_state.in_progress:
        return {
            "type": "continue",
            "issue": journey_state.current_issue,
            "reason": "You're working on this issue"
        }

    # Priority 2: Suggest next difficulty level
    if journey_state.recently_merged:
        next_level = suggest_next_difficulty(journey_state)
        return {
            "type": "progress",
            "suggestion": next_level,
            "reason": f"You completed a {journey_state.last_type}. Try a {next_level}."
        }

    # Priority 3: Top match
    if matches:
        top = matches[0]
        return {
            "type": "recommend",
            "issue": top,
            "reason": top.why_matched
        }

    # Priority 4: No matches — suggest broadening
    return {
        "type": "explore",
        "reason": "Try broadening your language filters or exploring new areas."
    }
```

---

## 26. AI vs Deterministic Logic

### Deterministic (No AI Needed)

| Task | Method | Why |
|------|--------|-----|
| Skill match scoring | Cosine similarity | Mathematical, precise |
| Popularity scoring | Star/fork/comment counts | GitHub API data |
| Freshness scoring | Issue age calculation | Date math |
| Readiness evaluation | Category overlap | Set intersection |
| Level calculation | Merged PR count | Simple formula |
| Competition analysis | Linked PR count | GitHub API data |
| Next move selection | State machine | Rule-based |
| Preparation plan (basic) | CONTRIBUTING.md check | File existence |

### AI-Enhanced (Groq LLM)

| Task | Method | Why |
|------|--------|-----|
| Skill fingerprinting | LLM analysis of repos | Nuanced understanding |
| Issue skill extraction | LLM analysis of text | Context comprehension |
| Readiness explanation | LLM reasoning | Personalized language |
| Preparation plan (rich) | LLM generation | Context-aware steps |
| Match explanation | LLM reasoning | Human-quality text |
| Query parsing | LLM intent extraction | Natural language understanding |

### Decision Rule

> **Use AI only when:** The task requires understanding context, nuance, or generating natural language. Use deterministic logic when the task can be solved with data + math.

---

## 27. Cost Optimization Strategy

### Current Architecture

| Strategy | Implementation |
|----------|---------------|
| Cache-first | Redis with probabilistic early expiry |
| Deduplication | In-flight request tracking |
| AI sparingly | Only for reasoning-heavy tasks |
| TTL-based expiry | Skill analysis cached 24h, embeddings 24h |
| Hash-based fallback | Regex analysis when AI unavailable |

### Target Cost Budget

| Resource | Monthly Budget | Notes |
|----------|---------------|-------|
| Groq API | < $5 | 2 calls/session, cached |
| Jina Embeddings | < $3 | Cached 24h |
| PostgreSQL | $0 | Free tier (Supabase) |
| Redis | $0 | Free tier (Upstash) |
| Render | $7 | Starter plan |
| **Total** | **< $15/month** | |

---

## 28. Trust, Safety and Transparency

### Transparency Rules

| Rule | Implementation |
|------|---------------|
| Never hide reasoning | Every recommendation has `why_matched` |
| Show confidence | Match score is a percentage, not a label |
| Present signals, not facts | "Estimated: Active maintainers" not "Maintainers are active" |
| Acknowledge limitations | "Competition data is based on visible PRs" |
| No fabricated data | All data from GitHub API or AI analysis, never invented |

### Trust Signals

| Signal | Display |
|--------|---------|
| Match score | Percentage with color coding |
| Skill overlap | Explicit skill badges |
| Repo activity | Stars, last commit, contributor count |
| Difficulty | Complexity score with label |
| Competition | Number of active PRs on issue |
| Readiness | "Ready" / "Almost ready" / "Not ready" |

---

## 29. Competitive Analysis

| Platform | What It Does | How IssueCompass Differs |
|----------|-------------|-------------------------|
| GitHub Issue Search | Filter by label, language, state | We personalize based on YOUR skills |
| GitHub Explore | Trending repos, curated lists | We recommend based on fit, not popularity |
| Good First Issue | Lists beginner issues | We assess YOUR readiness for each issue |
| CodeTriage | Daily email with one issue | We provide a full journey, not random issues |
| Up For Grabs | Curated beginner issues | We match by skill, not just label |

### Key Differentiator

> **IssueCompass is the only platform that provides a personalized contribution journey — not just issue discovery.**

---

## 30. Key Differentiators

| Differentiator | Description |
|----------------|-------------|
| **Personalized Journey** | Not just "find issues" but "here's your next step" |
| **Readiness Evaluation** | "Are you ready? What do you need to learn?" |
| **Explainable Scoring** | Every recommendation comes with "because..." |
| **Progression Tracking** | Levels based on real contribution capability |
| **Hybrid Intelligence** | AI for reasoning, algorithms for everything else |
| **Preparation Plans** | Step-by-step guides before attempting issues |
| **Low Cost** | < $15/month operating cost |

---

## 31. UX/UI Requirements

### Design Principles

| Principle | Description |
|-----------|-------------|
| Clean & Focused | Minimal UI, maximum signal |
| Progressive Disclosure | Show summary first, details on demand |
| Action-Oriented | Every card has a clear next action |
| Transparent | Show scoring rationale everywhere |
| Responsive | Desktop-first, mobile-friendly |

### Key UI Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Next Move Card | Dashboard top | "YOUR NEXT MOVE" recommendation |
| Project Card | Project list | Repository with fit score |
| Issue Card | Issue list | Issue with match score + readiness |
| Readiness Badge | Issue detail | Ready/Almost/Not ready indicator |
| Journey Tracker | Dashboard sidebar | Progress through contribution states |
| Level Badge | Profile | Current Open Source Level |
| Skill Fingerprint | Profile + Dashboard | Radar chart of skills |
| Preparation Panel | Issue detail | Step-by-step preparation plan |

---

## 32. Dashboard Structure

### Current Dashboard

```
┌─────────────────────────────────────────┐
│ [Navbar]                                │
├──────────┬──────────────────────────────┤
│ Sidebar  │ Main Content                 │
│          │                              │
│ Skill    │ [Search Bar]                 │
│ Finger-  │ [Filters: Language | Label]  │
│ print    │                              │
│          │ [Issue Card]                 │
│          │ [Issue Card]                 │
│          │ [Issue Card]                 │
│          │ ...                          │
└──────────┴──────────────────────────────┘
```

### Target Dashboard (v2.0)

```
┌─────────────────────────────────────────────────┐
│ [Navbar]                                        │
├──────────┬──────────────────────────────────────┤
│ Sidebar  │ Main Content                         │
│          │                                      │
│ Level    │ ┌──────────────────────────────────┐ │
│ Badge    │ │ YOUR NEXT MOVE                   │ │
│          │ │ "Contribute to fastapi/fastapi"  │ │
│ Skill    │ │ because your Python skills align  │ │
│ Finger-  │ │ and the repo has active maint... │ │
│ print    │ │ [View Project] [Skip]            │ │
│          │ └──────────────────────────────────┘ │
│ Current  │                                      │
│ Journey  │ [Search Bar]                         │
│ Progress │ [Filters]                            │
│          │                                      │
│          │ Recommended Projects:                │
│          │ [Project Card] [Project Card]        │
│          │                                      │
│          │ Recommended Issues:                  │
│          │ [Issue Card] [Issue Card]            │
│          │ [Issue Card] ...                     │
│          │                                      │
│          │ Your Journey:                        │
│          │ [Journey Tracker]                    │
└──────────┴──────────────────────────────────────┘
```

---

## 33. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Time to first match | < 60 seconds | Dashboard load → first match visible |
| Match relevance | > 70% user satisfaction | Post-match survey (Phase 2) |
| User return rate | > 40% weekly | Analytics |
| Contribution completion | > 20% of saved issues → PR | Journey tracking |
| PR merge rate | > 50% of submitted PRs | GitHub API monitoring |
| AI cost per session | < $0.01 | API billing |
| Cache hit rate | > 80% | Redis metrics |
| API response time (p99) | < 500ms | Monitoring middleware |

---

## 34. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| GitHub API rate limits | High | Medium | Aggressive caching, token rotation |
| Groq API downtime | Medium | Low | Graceful fallback to regex analysis |
| Low user adoption | High | Medium | Focus on GSoC season, university outreach |
| Incorrect readiness evaluation | Medium | Medium | Conservative thresholds, user feedback loop |
| Stale recommendation data | Medium | Medium | TTL-based caching, background refresh |
| Cost overrun | Low | Low | Budget alerts, cache-first architecture |

---

## 35. MVP Acceptance Criteria

### Must Pass (Phase 1 Complete)

| # | Criteria | Test |
|---|----------|------|
| 1 | User can sign in via GitHub OAuth | Login flow works end-to-end |
| 2 | User's skill fingerprint is generated | Profile shows languages, skills, categories |
| 3 | Repository recommendations are shown | Top 5 repos with fit scores |
| 4 | Readiness evaluation works | "Ready" / "Not ready" for any issue |
| 5 | Preparation plans are displayed | 3-5 steps shown per issue |
| 6 | "Next Move" widget shows on dashboard | Prominent card with recommendation |
| 7 | Journey tracking works | States update correctly |
| 8 | All recommendations have explanations | No "black box" scores |
| 9 | AI costs remain < $0.01/session | Billing monitored |
| 10 | p99 response time < 500ms | Performance tested |

---

## 36. Future Opportunities

### Phase 3+ Features

| Feature | Description | Impact |
|---------|-------------|--------|
| Notification System | Email/webhook when matching issues appear | Engagement |
| Repository Follow | Follow repos for new issues | Retention |
| Team Matching | Match issues for teams/orgs | Enterprise |
| AI Preparation Plans | Groq-powered context-aware plans | Quality |
| Contribution Portfolio | Visual portfolio of merged PRs | Portfolio value |
| Learning Paths | Structured learning recommendations | Education |
| GSoC Mode | Specialized flow for GSoC applicants | Seasonal |
| API Access | Public API for third-party integrations | Ecosystem |
| Browser Extension | Show readiness score on GitHub issue pages | Convenience |
| Mobile App | Native mobile experience | Accessibility |

---

## Appendix A: File Structure (Current)

```
IssueCompass/
├── backend/
│   ├── main.py                    # FastAPI entrypoint
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # 30+ env vars
│   │   │   ├── database.py        # Async SQLAlchemy + pgvector
│   │   │   ├── cache.py           # Redis with stampede protection
│   │   │   ├── dependencies.py    # JWT auth
│   │   │   ├── monitoring.py      # Request logging
│   │   │   ├── ratelimit.py       # SlowAPI config
│   │   │   └── utils.py           # DateTime parsing
│   │   ├── models/
│   │   │   └── models.py          # 4 ORM models
│   │   ├── schemas/
│   │   │   └── schemas.py         # 18 Pydantic models
│   │   ├── routes/
│   │   │   ├── auth.py            # 4 endpoints
│   │   │   ├── github.py          # 3 endpoints
│   │   │   └── issues.py          # 7 endpoints
│   │   ├── services/
│   │   │   ├── ai_service.py      # Groq + Jina
│   │   │   ├── github_service.py  # GitHub API client
│   │   │   ├── matching_service.py # Hybrid matching
│   │   │   ├── scoring_service.py  # 12-factor scoring
│   │   │   ├── search_service.py   # NLP search
│   │   │   └── skill_service.py   # Skill fingerprinting
│   │   └── worker.py              # ARQ background worker
│   ├── alembic/                   # 4 migrations
│   └── tests/                     # 237 test functions
│
├── frontend/
│   └── src/
│       ├── app/                   # 6 pages
│       ├── components/            # 9 components
│       ├── lib/                   # API, types, hooks
│       └── styles/                # Tailwind CSS
│
├── docker-compose.yml             # 5 services
├── render.yaml                    # Render Blueprint
└── .github/workflows/ci.yml       # 7-job CI pipeline
```

## Appendix B: New Files to Create (v2.0)

```
backend/app/
├── services/
│   ├── project_service.py         # NEW
│   ├── readiness_service.py       # NEW
│   ├── journey_service.py         # NEW
│   └── level_service.py           # NEW
├── routes/
│   ├── repos.py                   # NEW
│   ├── recommendations.py         # NEW
│   └── journey.py                 # NEW
└── tests/
    ├── test_project_service.py    # NEW
    ├── test_readiness_service.py  # NEW
    ├── test_journey_service.py    # NEW
    └── test_level_service.py      # NEW

frontend/src/
├── app/
│   ├── projects/page.tsx          # NEW
│   └── journey/page.tsx           # NEW
├── components/
│   ├── NextMoveCard.tsx           # NEW
│   ├── ProjectCard.tsx            # NEW
│   ├── ReadinessBadge.tsx         # NEW
│   ├── JourneyTracker.tsx         # NEW
│   ├── PreparationPlan.tsx        # NEW
│   └── LevelBadge.tsx             # NEW
└── lib/hooks/
    ├── use-recommendations.ts     # NEW
    ├── use-journey.ts             # NEW
    └── use-readiness.ts           # NEW
```

---

*End of PRD*

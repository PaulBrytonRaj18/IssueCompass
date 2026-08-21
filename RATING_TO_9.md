# IssueCompass — From 7.2 to 9.0+

> **Goal:** Raise every dimension to 9.0+ as an open source project
> **Framing:** Free, community-driven, ad/donation supported
> **Current Rating:** 7.2 / 10
> **Target Rating:** 9.0+ / 10

---

## Where We Are Now

```
Current:  7.2/10
Target:   9.0/10
Gap:      1.8 points across 8 dimensions
```

The two biggest drags are:
- **PRD Fulfillment: 4.5** → Need 9.0 (biggest gap: +4.5)
- **Open Source: 5.5** → Need 9.0 (second biggest: +3.5)

The strategy is simple: **fix the two worst dimensions first.** A 9-point project with two 4.5s looks like a 7. If we raise PRD Fulfillment and Open Source to 8+, the overall score jumps to 8.5+. Then polish everything else to push past 9.

---

## The 9.0 Scorecard

```
Dimension              Now    Target   Gap    How
─────────────────────────────────────────────────────
Idea                 8.5    9.0     +0.5   Validate with users
Codebase             7.5    9.0     +1.5   Testing + frontend quality
Open Source          5.5    9.0     +3.5   Community + contribution experience
Product              6.0    9.0     +3.0   Journey layer + onboarding
Learning Value       9.0    9.5     +0.5   Integration tests + docs
Business             6.5    N/A     ---    Not relevant (open source)
Technical            8.0    9.0     +1.0   Performance + security
PRD Fulfillment      4.5    9.0     +4.5   Build missing features
─────────────────────────────────────────────────────
OVERALL              7.2    9.0+    +1.8
```

---

## Phase 0: The Foundation (Week 1-2)

> *"You can't build a community on a broken foundation."*

Before anything else, fix the things that make contributors bounce.

### 0.1 Make It Actually Runnable (2 hours)

Right now, a new contributor needs 9+ environment variables (GitHub OAuth, Groq API, Jina API, etc.) to even start the project. This kills adoption.

**What to build:**
```
docker-compose.dev.yml  — A dev config with:
  - Mock AI responses (no Groq/Jina keys needed)
  - Pre-seeded demo data
  - GitHub OAuth optional (skip with mock user)
  - One command: docker-compose -f docker-compose.dev.yml up
```

**Why this matters:**
A contributor who can't run the project in 5 minutes will never contribute. Period.

**Impact:** Open Source 5.5 → 6.5, Product 6.0 → 6.5

### 0.2 Make It Contributeable (1 hour)

**Add to the repo:**
```markdown
.github/
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   ├── feature_request.md
│   └── question.md
├── PULL_REQUEST_TEMPLATE.md
└── FUNDING.yml          # GitHub Sponsors + Buy Me a Coffee
CODE_OF_CONDUCT.md       # Contributor Covenant v2.1
good-first-issue labels  # Tag 10 issues as "good first issue"
```

**Enhance CONTRIBUTING.md (currently 82 lines → 300+ lines):**
```markdown
# Contributing to IssueCompass

## Quick Start
1. Fork the repo
2. Run `docker-compose -f docker-compose.dev.yml up`
3. Open http://localhost:3000
4. Pick a "good first issue" from the Issues tab

## Development Setup
[Detailed steps with screenshots]

## Code Style
- Backend: ruff check + ruff format
- Frontend: next lint + prettier
- Run `pre-commit install` for automatic checks

## Architecture Overview
[Brief version of ARCHITECTURE.md for quick context]

## How to Add a New Feature
1. Create a branch
2. Add the route/service/schema
3. Write tests
4. Update the PRD
5. Submit PR

## How to Add a New API Endpoint
[Step-by-step with example]

## How to Run Tests
[Commands]

## Getting Help
- Open a "Question" issue
- Join our Discord (if created)
- Tag @PaulBrytonRaj18
```

**Why this matters:**
CONTRIBUTING.md is the front door. If it's vague, no one walks in.

**Impact:** Open Source 5.5 → 6.0

### 0.3 Make It Look Trustworthy (30 minutes)

**Update README.md with:**
```markdown
# IssueCompass

> AI-powered Open Source Contribution Compass

![CI](https://github.com/PaulBrytonRaj18/IssueCompass/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)
![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)

![Dashboard Screenshot](docs/screenshot-dashboard.png)
![Profile Screenshot](docs/screenshot-profile.png)

## What is IssueCompass?

[1-paragraph description]

## Demo

[30-second GIF or link to live demo]

## Quick Start

[3 commands to get running]

## Features

- ✅ AI-powered skill fingerprinting
- ✅ Personalized issue matching
- ✅ Smart search with natural language
- ✅ Contribution journey tracking
- ✅ Readiness evaluation
- ✅ [etc.]

## Architecture

[Brief diagram, link to ARCHITECTURE.md]

## Contributing

[Link to CONTRIBUTING.md]

## License

MIT
```

**Why this matters:**
People judge repos in 10 seconds. Badges, screenshots, and a clear README are the difference between "star" and "bounce."

**Impact:** Open Source 5.5 → 6.0, Idea 8.5 → 8.5 (maintained)

---

## Phase 1: The Missing Product Layer (Week 3-8)

> *"The PRD's vision is a contribution journey. Build that."*

This is the biggest gap. The project currently matches issues. The PRD wants it to guide a journey. These are different products.

### 1.1 "Next Move" Widget (Week 3, 3-5 days)

**What:** A prominent card at the top of the dashboard that tells the user exactly what to do next.

**Backend:**
```
GET /api/v1/recommendations/next-move
→ Returns: { type, recommendation, reason, action_url }
```

**Logic:**
```python
def get_next_move(user):
    # 1. If in-progress contribution → "Continue working on X"
    # 2. If recently merged → "Try a [harder] [type] issue"
    # 3. If has matches → "Top recommendation: X"
    # 4. If no skills → "Analyze your profile first"
    # 5. If no matches → "Try broadening your filters"
```

**Frontend:**
```tsx
<NextMoveCard
  title="YOUR NEXT MOVE"
  recommendation="Contribute to fastapi/fastapi"
  reason="Your Python skills match and the repo has active maintainers"
  action={{ label: "View Project", url: "/projects/fastapi/fastapi" }}
  skip={{ label: "Skip", onClick: handleSkip }}
/>
```

**Why this matters:**
This is the single most impactful UI element. It answers the PRD's core question: "What should I contribute to next?"

**Impact:** Product 6.0 → 7.0, PRD Fulfillment 4.5 → 5.5

### 1.2 Repository Discovery (Week 3-4, 1-2 weeks)

**What:** Recommend repositories, not just issues. Show project-level fit scores.

**Backend:**
```
GET /api/v1/repos/recommended?limit=10
→ Returns: [{ repo, fit_score, explanation, issue_count, activity_score }]

GET /api/v1/repos/{full_name}
→ Returns: { repo, fit_score, score_breakdown, similar_repos, top_issues }
```

**Scoring:**
```python
PROJECT_WEIGHTS = {
    "skill_match": 0.30,           # User skills vs repo tech
    "activity": 0.20,              # Recent commits, releases
    "contributor_friendliness": 0.15,  # CONTRIBUTING.md, GFI count
    "issue_availability": 0.15,    # Open issues matching user
    "learning_value": 0.10,        # New tech for user
    "portfolio_value": 0.10,       # Repo popularity
}
```

**Frontend:**
```
/projects                  — List of recommended projects
/projects/{full_name}      — Project detail with fit score + top issues
```

**Why this matters:**
The PRD says "recommend repositories instead of only recommending issues." This is the core differentiator.

**Impact:** Product 6.0 → 7.5, PRD Fulfillment 4.5 → 6.0

### 1.3 Readiness Evaluation (Week 5, 1 week)

**What:** Before showing an issue, evaluate if the user is ready for it.

**Backend:**
```
GET /api/v1/issues/{id}/readiness
→ Returns: { status: "ready"|"almost_ready"|"not_ready", missing_skills: [], explanation: "..." }
```

**Logic:**
```python
def evaluate_readiness(user_skills, issue_required):
    user_cats = set(user_skills.get("categories", {}).keys())
    issue_cats = set(issue_required.get("categories", {}).keys())

    covered = user_cats & issue_cats
    missing = issue_cats - user_cats
    coverage = len(covered) / max(len(issue_cats), 1)

    if coverage >= 0.8:
        return "ready", [], "You have the skills for this issue."
    elif coverage >= 0.5:
        return "almost_ready", list(missing), f"You should learn {', '.join(missing)} first."
    else:
        return "not_ready", list(missing), f"This issue requires {', '.join(missing)} which you haven't demonstrated yet."
```

**Frontend:**
```tsx
<ReadinessBadge status="almost_ready" />
// Shows: 🟡 Almost Ready — "You should learn React Query before attempting this"
```

**Why this matters:**
The PRD asks: "Am I ready for this issue?" This answers it.

**Impact:** Product 6.0 → 8.0, PRD Fulfillment 4.5 → 6.5

### 1.4 Preparation Plans (Week 5-6, 1 week)

**What:** For each recommended issue, show a 3-5 step preparation plan.

**Backend:**
```
GET /api/v1/issues/{id}/preparation
→ Returns: { steps: [{ title, description, link, estimated_time }] }
```

**Rule-based plan (Phase 1):**
```python
def generate_preparation_plan(issue, repo, user_experience):
    steps = []

    # Step 1: Always — understand the repo
    steps.append({
        "title": "Read the README",
        "description": f"Understand what {repo.full_name} does and how it's structured.",
        "link": f"https://github.com/{repo.full_name}#readme",
        "estimated_time": "10 min"
    })

    # Step 2: If CONTRIBUTING.md exists
    if has_contributing_md(repo):
        steps.append({
            "title": "Read CONTRIBUTING.md",
            "description": "Understand how to contribute to this project.",
            "link": f"https://github.com/{repo.full_name}/blob/main/CONTRIBUTING.md",
            "estimated_time": "10 min"
        })

    # Step 3: Run the project locally
    steps.append({
        "title": "Set up the project locally",
        "description": "Fork, clone, and run the project on your machine.",
        "link": f"https://github.com/{repo.full_name}#getting-started",
        "estimated_time": "30 min"
    })

    # Step 4: Review related PRs
    steps.append({
        "title": "Review 2-3 recent merged PRs",
        "description": "See how other contributors approached similar issues.",
        "link": f"https://github.com/{repo.full_name}/pulls?q=is%3Apr+is%3Amerged",
        "estimated_time": "20 min"
    })

    # Step 5: If beginner — skip advanced steps
    if user_experience != "advanced":
        steps.append({
            "title": "Look for similar open issues",
            "description": "Find simpler issues in the same area to warm up.",
            "link": f"https://github.com/{repo.full_name}/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22",
            "estimated_time": "10 min"
        })

    return steps
```

**Frontend:**
```tsx
<PreparationPlan steps={[
  { title: "Read the README", time: "10 min", done: true },
  { title: "Read CONTRIBUTING.md", time: "10 min", done: true },
  { title: "Set up locally", time: "30 min", done: false },
  { title: "Review recent PRs", time: "20 min", done: false },
  { title: "Find warm-up issues", time: "10 min", done: false },
]} />
```

**Why this matters:**
The PRD says: "Help me become good enough to make the contribution." This is how.

**Impact:** Product 6.0 → 8.5, PRD Fulfillment 4.5 → 7.0

### 1.5 Contribution Journey Tracking (Week 6-7, 1-2 weeks)

**What:** Track the user's journey from discovery to merged contribution.

**Enhance SavedIssue model:**
```sql
ALTER TABLE saved_issues ADD COLUMN github_pr_url VARCHAR(500);
ALTER TABLE saved_issues ADD COLUMN pr_status VARCHAR(50);
ALTER TABLE saved_issues ADD COLUMN pr_submitted_at TIMESTAMPTZ;
ALTER TABLE saved_issues ADD COLUMN pr_merged_at TIMESTAMPTZ;
ALTER TABLE saved_issues ADD COLUMN started_at TIMESTAMPTZ;
ALTER TABLE saved_issues ADD COLUMN preparation_completed BOOLEAN DEFAULT FALSE;
```

**Backend:**
```
PUT /api/v1/saved/{id}/journey
→ Body: { status: "in_progress" | "submitted", github_pr_url: "..." }
→ Updates journey state

GET /api/v1/saved/journey
→ Returns: [{ issue, status, pr_url, submitted_at, merged_at }]
```

**Background worker (new cron):**
```python
async def check_pr_status(ctx):
    """Check PR status for all submitted issues every 2 hours."""
    async with AsyncSessionLocal() as db:
        submitted = await db.execute(
            select(SavedIssue).where(SavedIssue.pr_status == "open")
        )
        for saved in submitted.scalars():
            pr_status = await github_service.get_pr_status(saved.github_pr_url)
            saved.pr_status = pr_status
            if pr_status == "merged":
                saved.pr_merged_at = datetime.now(timezone.utc)
        await db.commit()
```

**Frontend:**
```
/saved — Shows journey progress for each saved issue
        Status badges: 💾 Saved → 🔨 In Progress → 📤 Submitted → ✅ Merged
```

**Why this matters:**
The PRD's entire contribution journey depends on this. Without tracking, there's no journey.

**Impact:** Product 6.0 → 8.5, PRD Fulfillment 4.5 → 7.5

### 1.6 Open Source Level System (Week 7-8, 1 week)

**What:** Non-gamified progression model based on real contribution capability.

**Levels:**
```
Level 1 — Explorer        (0 merged PRs)
Level 2 — First Contributor  (1+ merged PRs)
Level 3 — Active Contributor (5+ merged PRs, 2+ repos)
Level 4 — Reliable Contributor (15+ merged PRs, 3+ repos, features)
Level 5 — Project Contributor  (30+ merged PRs, deep involvement)
```

**Backend:**
```
GET /api/v1/users/me/level
→ Returns: { level: 3, name: "Active Contributor", progress: 0.6, next_level_requirements: [...] }
```

**Calculation (deterministic, no AI):**
```python
def calculate_level(merged_prs, repos_contributed, has_features):
    if merged_prs == 0: return 1
    if merged_prs >= 1 and repos_contributed == 1: return 2
    if merged_prs >= 5 and repos_contributed >= 2: return 3
    if merged_prs >= 15 and repos_contributed >= 3 and has_features: return 4
    if merged_prs >= 30: return 5
    return max(1, min(4, merged_prs // 5 + 1))
```

**Frontend:**
```tsx
<LevelBadge level={3} name="Active Contributor" />
// On profile page: progress bar to Level 4
```

**Why this matters:**
The PRD wants progression. Levels make it visible and motivating.

**Impact:** Product 6.0 → 9.0, PRD Fulfillment 4.5 → 8.0

---

## Phase 2: Community Building (Week 4-12, Parallel)

> *"An open source project without a community is just a repo."*

### 2.1 Be the First Contributor Yourself (Week 4-8)

Before asking others to contribute, demonstrate the contribution experience yourself.

**Do this:**
1. Open 15-20 issues of varying difficulty (good first issue, medium, hard)
2. Write clear issue descriptions with acceptance criteria
3. Tag them appropriately
4. Create a `v1.0.0` release
5. Write a CHANGELOG.md

**Why:**
Contributors look at the Issues tab first. Empty issues = dead project. Active issues = living project.

### 2.2 Content Marketing (Week 6-10)

Open source projects die in silence. You need to be loud.

**Write 3-5 blog posts:**
1. "How I Built an AI-Powered Open Source Contribution Platform" (Dev.to / Hashnode)
2. "Using pgvector for Semantic Issue Matching" (technical deep dive)
3. "How IssueCompass Uses Groq LLM to Analyze Developer Skills" (AI angle)
4. "From Good First Issue to Contribution Journey: The Future of Open Source" (vision)

**Post on:**
- Reddit: r/opensource, r/webdev, r/Python, r/nextjs
- Hacker News: "Show HN: IssueCompass"
- Dev.to, Hashnode, Medium
- Twitter/X with screenshots
- Discord communities (React, Python, FastAPI, open source)

**Why:**
The best open source projects are also content projects. Kubernetes has a blog. React has a blog. You need content that drives traffic to the repo.

### 2.3 Make Contributing Rewarding (Week 8-12)

**Add to the README:**
```markdown
## Contributors

Thanks to all the people who have contributed!

<a href="https://github.com/PaulBrytonRaj18/IssueCompass/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=PaulBrytonRaj18/IssueCompass" />
</a>
```

**Add to the profile page:**
```markdown
Your Open Source Level: 🌿 Active Contributor
Merged PRs: 8 across 3 repositories
```

**Create a Discord server (optional):**
- #general — discussion
- #help — get help
- #contributing — contribution questions
- #announcements — releases and updates

**Why:**
People contribute to projects where they feel welcome and recognized.

---

## Phase 3: Codebase Quality (Week 8-14)

> *"A 9/10 codebase has tests, types, and documentation everywhere."*

### 3.1 Frontend Testing (Week 8-10)

Currently: 3 test cases. Target: 50+.

**Priority components to test:**
```
1. IssueCard.tsx          — renders match score, labels, save button
2. Navbar.tsx             — renders links, auth state
3. SkillFingerprint.tsx   — renders radar chart, categories
4. Dashboard page         — loads matches, shows filters
5. Profile page           — shows fingerprint, categories
6. Saved page             — shows saved issues
```

**Test pattern:**
```typescript
// IssueCard.test.tsx
describe("IssueCard", () => {
  it("renders match score as percentage", () => {
    render(<IssueCard match={mockMatch} />);
    expect(screen.getByText("87%")).toBeInTheDocument();
  });

  it("shows why_matched explanation", () => {
    render(<IssueCard match={mockMatch} />);
    expect(screen.getByText(/Python match/)).toBeInTheDocument();
  });

  it("calls save API when bookmark clicked", async () => {
    render(<IssueCard match={mockMatch} />);
    await userEvent.click(screen.getByLabelText("Save issue"));
    expect(mockSaveApi).toHaveBeenCalledWith(123);
  });
});
```

### 3.2 Integration Tests (Week 10-12)

Currently: 0 integration tests. Target: 20+.

**Test real database interactions:**
```python
# test_integration_matching.py
@pytest.mark.asyncio
async def test_full_matching_flow(test_db, test_user_with_skills):
    """Test: create user → index issues → get matches → verify scores."""
    # 1. Create user with skill_vector
    # 2. Index 10 issues with skill_vectors
    # 3. Call get_matched_issues
    # 4. Verify results are scored and ranked
    # 5. Verify cache is populated
```

**Test the API end-to-end:**
```python
# test_api_integration.py
@pytest.mark.asyncio
async def test_auth_flow(test_client):
    """Test: login → get profile → analyze → get matches."""
    # 1. POST /auth/github/callback (mock GitHub data)
    # 2. GET /auth/me (verify user created)
    # 3. POST /github/analyze/{username} (mock GitHub repos)
    # 4. GET /issues/matches (verify matches returned)
```

### 3.3 Performance Audit (Week 12-13)

**Add:**
- `pyproject.toml` with ruff, mypy, pytest config
- Database query logging in debug mode
- Response time headers (`X-Response-Time`)
- Load testing script (Locust or k6)

**Target metrics:**
```
GET /issues/matches    — p99 < 500ms
GET /issues/trending   — p99 < 300ms
GET /repos/recommended — p99 < 400ms
POST /auth/callback    — p99 < 200ms
```

### 3.4 Security Hardening (Week 13-14)

**Add:**
- CSP headers (Content-Security-Policy)
- Rate limiting on all endpoints (verify)
- Input validation audit (Pydantic models)
- Dependency vulnerability scan (safety / pip-audit)
- `.env.example` with all required variables documented

---

## Phase 4: Product Polish (Week 12-16)

> *"A 9/10 product makes you feel something."*

### 4.1 Onboarding Flow (Week 12-13)

**When a user signs in for the first time:**
```
Step 1: "Welcome to IssueCompass!"
        → Brief explanation of what the product does

Step 2: "Analyzing your GitHub profile..."
        → Show progress animation
        → Display skill categories as they're detected

Step 3: "Here's your Open Source DNA"
        → Show radar chart
        → Show top skills
        → "You're ready to find issues!"

Step 4: "Your first recommendation"
        → Show "Next Move" card
        → Guide to first issue
```

**Why:**
The current first-time experience is "Loading..." then empty state. Onboarding should feel like magic.

### 4.2 Dashboard Redesign (Week 13-15)

**Current dashboard:**
```
[Sidebar: Skill Fingerprint] [Main: Issue Cards]
```

**Target dashboard:**
```
┌─────────────────────────────────────────────────┐
│ YOUR NEXT MOVE                                  │
│ "Contribute to fastapi/fastapi"                 │
│ because your Python skills match and...          │
│ [View Project] [Skip]                           │
├─────────────────────────────────────────────────┤
│ Recommended Projects                            │
│ [ProjectCard] [ProjectCard] [ProjectCard]       │
├─────────────────────────────────────────────────┤
│ Your Journey                                    │
│ [JourneyTracker: 3 saved, 1 in progress]       │
├─────────────────────────────────────────────────┤
│ Recommended Issues                              │
│ [IssueCard] [IssueCard] [IssueCard]             │
└─────────────────────────────────────────────────┘
```

### 4.3 Error States and Empty States (Week 14-15)

**Current:** Generic "No matches yet"

**Target:** Contextual empty states:
```
No skills yet → "Analyze your profile to get personalized matches"
No matches    → "Try broadening your language filters"
API down      → "We're having trouble connecting. Try again in a moment."
Rate limited  → "You've been browsing a lot! Take a break and come back."
```

### 4.4 Mobile Responsive (Week 15-16)

**Current:** Desktop-focused

**Target:** Works on mobile:
- Stack sidebar below main content
- Collapse filters into a drawer
- Issue cards full-width
- Journey tracker as horizontal scroll

---

## Phase 5: Documentation as Code (Week 14-16)

> *"Great documentation is the difference between 10 stars and 1000 stars."*

### 5.1 Enhanced ARCHITECTURE.md

Add:
- Decision records (why FastAPI over Django, why pgvector over Pinecone)
- Scaling considerations
- Cost analysis
- Comparison with alternatives

### 5.2 API Documentation

Enhance Swagger with:
- Request/response examples
- Authentication flow diagrams
- Rate limit documentation
- Error code reference

### 5.3 Video Walkthrough

Record a 5-minute video:
1. What IssueCompass does (30 sec)
2. How to run it locally (1 min)
3. How to contribute (1 min)
4. Architecture overview (1 min)
5. Feature demo (1.5 min)

Post on YouTube, link from README.

### 5.4 Changelog

Create CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/):
```markdown
# Changelog

## [1.1.0] - 2026-09-15
### Added
- Repository discovery with project fit scores
- Readiness evaluation for issues
- Preparation plans
- Contribution journey tracking
- Open Source Level system
- "Next Move" dashboard widget

### Changed
- Dashboard redesign with journey tracker
- Enhanced skill fingerprinting

### Fixed
- Docker port mismatch bug
- Missing fields on live ORM objects

## [1.0.0] - 2026-08-21
### Added
- GitHub OAuth authentication
- AI-powered skill fingerprinting
- Hybrid issue matching (DB + live GitHub)
- Smart search with NLP
- Background issue indexing
```

---

## The Math: How We Get to 9.0

### Current → Target by Dimension

```
Dimension           Now   After Phase 0  After Phase 1  After Phase 2  After Phase 3  Final
─────────────────────────────────────────────────────────────────────────────────────────────
Idea               8.5      8.5            9.0            9.0            9.0          9.0
Codebase           7.5      7.5            7.5            7.5            9.0          9.0
Open Source        5.5      6.5            7.0            9.0            9.0          9.0
Product            6.0      6.5            9.0            9.0            9.5          9.5
Learning Value     9.0      9.0            9.0            9.0            9.5          9.5
Technical          8.0      8.0            8.0            8.0            9.0          9.0
PRD Fulfillment    4.5      5.0            8.5            8.5            9.0          9.0
─────────────────────────────────────────────────────────────────────────────────────────────
OVERALL            7.2      7.3            8.2            8.7            9.2          9.2
```

### What Each Phase Buys Us

| Phase | Focus | Rating Impact | Key Deliverable |
|-------|-------|---------------|-----------------|
| 0 | Foundation | +0.1 | Anyone can run it in 5 minutes |
| 1 | Product Layer | +0.9 | Journey + readiness + preparation |
| 2 | Community | +0.5 | Contributors, content, presence |
| 3 | Code Quality | +0.5 | Tests, performance, security |
| 4 | Polish | +0.5 | Onboarding, dashboard, mobile |
| 5 | Documentation | +0.3 | Docs, video, changelog |
| **Total** | | **+2.0** | **7.2 → 9.2** |

---

## Priority Matrix

```
                        HIGH IMPACT
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         │  Next Move       │  Integration     │
         │  Widget          │  Tests           │
         │                  │                  │
         │  Repo Discovery  │  Security Audit  │
         │                  │                  │
         │  Readiness Eval  │  Performance     │
         │                  │  Audit           │
HIGH     │──────────────────┼──────────────────│ LOW
EFFORT   │                  │                  │ EFFORT
         │  Contribution    │  Badges +        │
         │  Journey         │  Screenshots     │
         │                  │                  │
         │  Level System    │  Issue Templates │
         │                  │                  │
         │  Mobile          │  CONTRIBUTING.md │
         │  Responsive      │  Enhancement     │
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                        LOW IMPACT
```

**Strategy:** Do high-impact + low-effort first (top-right quadrant).

---

## The 9.0 Checklist

### ✅ Open Source (5.5 → 9.0)

- [ ] docker-compose.dev.yml with mock data
- [ ] Issue templates (bug, feature, question)
- [ ] PR template
- [ ] CODE_OF_CONDUCT.md
- [ ] Enhanced CONTRIBUTING.md (300+ lines)
- [ ] good-first-issue labels (10+ issues)
- [ ] Badges in README
- [ ] Screenshots/GIF in README
- [ ] v1.0.0 release
- [ ] CHANGELOG.md
- [ ] 5+ contributors (not just you)
- [ ] Blog posts (3+)
- [ ] Reddit/HN/Dev.to posts
- [ ] Contributors section in README
- [ ] FUNDING.yml (GitHub Sponsors)

### ✅ Product (6.0 → 9.0)

- [ ] "Next Move" widget
- [ ] Repository discovery page
- [ ] Project fit scores
- [ ] Readiness evaluation
- [ ] Preparation plans
- [ ] Contribution journey tracking
- [ ] PR status monitoring
- [ ] Open Source Level system
- [ ] Onboarding flow
- [ ] Dashboard redesign
- [ ] Contextual empty states
- [ ] Mobile responsive

### ✅ Codebase (7.5 → 9.0)

- [ ] 50+ frontend test cases
- [ ] 20+ integration tests
- [ ] Load testing script
- [ ] Performance audit
- [ ] Security hardening
- [ ] pyproject.toml with all tool configs
- [ ] Response time headers
- [ ] Dependency vulnerability scan

### ✅ PRD Fulfillment (4.5 → 9.0)

- [ ] All P0 features built
- [ ] All P1 features built
- [ ] Dashboard matches PRD structure
- [ ] All 17 API endpoints exist
- [ ] 7/7 DB tables exist
- [ ] Scoring uses all 10 PRD factors

---

## Timeline

```
Week  1-2:  Phase 0 — Foundation (runnable, contributeable, trustworthy)
Week  3-8:  Phase 1 — Product Layer (journey, readiness, preparation)
Week  4-12: Phase 2 — Community (content, issues, contributors) [parallel]
Week  8-14: Phase 3 — Code Quality (tests, performance, security) [parallel]
Week 12-16: Phase 4 — Product Polish (onboarding, dashboard, mobile)
Week 14-16: Phase 5 — Documentation (docs, video, changelog)
```

**Total: 16 weeks (4 months) from 7.2 to 9.0+**

---

## The One Thing That Matters Most

If you do only one thing from this document, do this:

> **Make the project runnable in one command with mock data, and open 15 good-first-issues.**

Everything else follows from that. A project people can run attracts contributors. Contributors build features. Features attract users. Users attract more contributors. It's a flywheel.

The flywheel starts with `docker-compose up`.

---

*End of Roadmap*

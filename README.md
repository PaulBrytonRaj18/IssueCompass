# 🗂️ OpenIssue

> **Match open-source contributors to issues they can actually solve.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/yourusername/openissue?style=social)](https://github.com/yourusername/openissue)

OpenIssue is a free, open-source platform that analyzes your GitHub activity, builds a personal **skill fingerprint**, and matches you to open-source issues you are actually capable of solving — so you stop scrolling and start contributing.

---

## 🚀 The Problem

- Developers want to contribute to open source but don't know where to start
- Maintainers tag issues but the wrong contributors show up
- GitHub's Explore tab is generic and useless for matching
- Tools like `goodfirstissue.dev` are just filtered lists — zero intelligence

## ✅ The Solution

OpenIssue analyzes **your actual GitHub repos, languages, dependencies, and commit history** to build a skill vector, then semantically matches you to issues across thousands of repos using **pgvector similarity search**.

---

## ✨ Features

- 🔐 **GitHub OAuth** — Login with one click, no password
- 🧬 **Skill Fingerprint** — Auto-generated from your real GitHub activity
- 🎯 **Smart Matching** — pgvector semantic search matches you to relevant issues
- 📋 **Issue Feed** — Personalized dashboard of matched issues updated daily
- 🏷️ **Filters** — By language, complexity, repo size, topic
- 📊 **Analytics** — Track your contributions and skill growth
- 📧 **Weekly Digest** — Email digest of new matched issues
- 🌍 **FOSS** — Completely free and open source forever

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11 |
| Database | PostgreSQL + pgvector |
| Cache | Redis |
| Auth | NextAuth.js + GitHub OAuth |
| Deployment | Docker Compose |

---

## 🏃 Quick Start

### Prerequisites

- Docker & Docker Compose
- GitHub OAuth App credentials ([create one here](https://github.com/settings/applications/new))

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/openissue.git
cd openissue
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your GitHub OAuth credentials and other values
```

### 3. Run with Docker

```bash
docker-compose up --build
```

### 4. Open in browser

```
Frontend: http://localhost:3000
Backend API: http://localhost:8000/docs
```

---

## 🔧 Manual Setup (Without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database

```bash
# Requires PostgreSQL with pgvector extension
psql -U postgres -c "CREATE DATABASE openissue;"
psql -U postgres -d openissue -c "CREATE EXTENSION vector;"
```

---

## 📁 Project Structure

```
openissue/
├── frontend/                 # Next.js application
│   └── src/
│       ├── app/              # App Router pages
│       ├── components/       # Reusable UI components
│       └── lib/              # API client, types, utilities
├── backend/                  # FastAPI application
│   └── app/
│       ├── routes/           # API route handlers
│       ├── services/         # Business logic
│       ├── models/           # Database models
│       ├── schemas/          # Pydantic schemas
│       └── core/             # Config, DB connection
├── docker-compose.yml
└── .env.example
```

---

## 🤝 Contributing

Contributions are what make open source amazing. Any contribution you make is **greatly appreciated**.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 🗺️ Roadmap

- [ ] pgvector semantic matching engine
- [ ] Email digest system
- [ ] Maintainer promotion dashboard
- [ ] Browser extension
- [ ] CLI tool
- [ ] Slack/Discord bot integration
- [ ] Contribution streak tracking

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

## ⭐ Show your support

Give a ⭐ if this project helped you find your first open source contribution!

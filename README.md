# 🌐 Binary Brain Institute Management System (BB-IMS)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-2563eb?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/React-19-0ea5e9?logo=react&logoColor=white" alt="React 19" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-00C7B7?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169e1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/License-MIT-10b981" alt="License" />
</p>

<h1 align="center">🌐 Binary Brain Institute Management System (BB-IMS)</h1>

<p align="center">
  <strong>A comprehensive educational institute management platform for small-to-medium coaching institutes, private schools, and training centers.</strong> Manages the full institute lifecycle through three interfaces sharing a single business logic layer.
</p>

---

## 📸 Screenshots

> To add screenshots: run `python main.py` for desktop or `npm run dev` for web, capture your screen, save images to `docs/assets/`, and reference them below.
>
> **Suggested screenshots:**
> - Desktop client dashboard with KPIs
> - React web dashboard (dark mode)
> - Student attendance management
> - Analytics dashboard with SHAP risk cards

---

## 📋 Table of Contents

- [Screenshots](#-screenshots)
- [Interfaces](#interfaces)
- [🧰 Tech stack](#-tech-stack)
- [🏗️ Architecture](#️-architecture)
- [Quick start](#-quick-start)
- [API reference](#api-reference)
- [Security](#security)
- [ML pipeline](#ml-pipeline)
- [Project structure](#project-structure)
- [Roadmap](#roadmap)
- [Contributing](#-contributing)
- [License](#license)

---

## Interfaces

| Interface | Stack | Users |
| --- | --- | --- |
| Desktop Client | CustomTkinter | Admin, Staff, Students (local/offline) |
| Web Dashboard | React 19 + Vite SPA | Admin, Staff (browser-based) |
| REST API | FastAPI /v1/ (50+ endpoints) | All clients, integrations |

Each interface talks to the same service layer — no duplicated business logic between the CLI, the web SPA, and the API.

## 🧰 Tech stack

| Category | Technology |
| --- | --- |
| Desktop client | Python 3.10+, CustomTkinter |
| Web dashboard | React 19 + Vite SPA |
| API | FastAPI 0.115+ |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x |
| Auth | JWT (RS256) + password hashing |
| Infra | Docker, GitHub Actions (lint, typecheck, test, security) |

## 🏗️ Architecture

```text
Institute-Management-System/
├── desktop/                   # CustomTkinter desktop client
├── web/                       # React 19 + Vite SPA
├── apis/                      # FastAPI /v1 service
│   ├── routes/                # Endpoints
│   ├── services/              # Shared business logic
│   ├── models/                # SQLAlchemy models
│   └── security/              # JWT, password hashing
├── db/                        # Alembic migrations
├── tests/                     # pytest suite
├── docker-compose.yml
└── requirements.txt
```

## Quick start

### Prerequisites

- Python 3.10 or newer
- Node.js 18+ (web dev)
- PostgreSQL 16 (or use the bundled SQLite for local dev)

### Option A — Desktop client

```bash
# 1. Clone the repository
git clone https://github.com/themanoj-025/Institute-Management-System.git
cd Institute-Management-System

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Apply database migrations
alembic upgrade heads

# 4. Run the desktop app
python main.py
```

### Option B — Web dashboard

```bash
# 1. Install Node dependencies (from the web directory)
cd web && npm install

# 2. Start the dev server
npm run dev
```

### Option C — REST API (all clients)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Apply migrations
alembic upgrade heads

# 3. Start the API
uvicorn apis.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the Swagger UI.

### Environment variables

| Variable | Default | Required | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | `sqlite:///ims.db` | No | Dev: SQLite. Prod: PostgreSQL. |
| `DATABASE_URL_POSTGRES` | `postgresql+psycopg2://user:pass@localhost/ims` | No | Production PostgreSQL |
| `JWT_SECRET` | — | Yes | JWT signing secret |
| `SECRET_KEY` | — | Yes | App secret key |
| `LOG_LEVEL` | `info` | No | Logging verbosity |

## 🔌 API reference

The FastAPI app exposes `/v1/` endpoints grouped by resource. Each endpoint calls a function in `apis/services/` inside a DB transaction and is covered by the test suite.

| Group | Endpoints |
| --- | --- |
| Students | `GET /v1/students`, `POST /v1/students`, `PATCH /v1/students/{id}` |
| Staff | `GET /v1/staff`, `POST /v1/staff`, `PATCH /v1/staff/{id}` |
| Courses & subjects | `GET /v1/courses`, `GET /v1/subjects` |
| Sessions | `GET /v1/sessions`, `POST /v1/sessions` |
| Attendance | `GET /v1/attendance`, `POST /v1/attendance` |
| Fees | `GET /v1/fees`, `POST /v1/fees`, `PATCH /v1/fees/{id}` |
| Reports | `GET /v1/reports/attendance`, `GET /v1/reports/fees` |
| Auth | `POST /v1/auth/login`, `POST /v1/auth/refresh` |

> [!NOTE] The OpenAPI docs live at `/docs` and `/redoc` served by FastAPI. A static spec is generated by CI so the published README stays truthful.

## 🔒 Security

- **JWT (RS256)** — short-lived access tokens with refresh rotation
- **Password hashing** — bcrypt via `passlib`
- **CORS** — scoped to the React dev server
- **Input validation** — Pydantic v2 schemas on every request
- **Dependency scans** — in CI (repository maintainer's `requirements.txt` pins)

> [!IMPORTANT] This is an educational-portfolio project. Do not expose it to untrusted external networks without hardening (rate limiting, email verification, MFA) and a third-party security review.

## 🏋️ ML pipeline

The ML pipeline is a separate service used by the analytics screens:

- **Training**: `python -m ml.train` — trains per-course/student performance models
- **Inference**: `/v1/ml/predict` — returns a risk score + explanation
- **Artifacts**: recorded in MLflow under the `ims-ml` experiment

## 📁 Project structure

```
Institute-Management-System/
├── desktop/                    # CustomTkinter desktop client
├── web/                        # React 19 + Vite SPA
├── apis/                       # FastAPI /v1 service
│   ├── routes/
│   ├── services/
│   ├── models/
│   └── security/
├── db/                         # Alembic migrations
├── tests/                      # pytest suite
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🚀 Deployment

### Docker

```bash
docker compose up --build
```

The compose file ships a `web` service (React), an `api` service (FastAPI), and a `db` service (PostgreSQL), with the desktop client bundled in the image.

## 🗺️ Roadmap

> [!CAUTION] Checked items are built and verified. Unchecked items are tracked in the issue tracker.

- [x] Desktop client (37 screens)
- [x] Web dashboard (React 19)
- [x] REST API (50+ endpoints)
- [x] Concurrent-safe transactions
- [ ] OAuth2 / SSO (tracked public issue)

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

## 📬 Support

- 🐛 [Report a bug](https://github.com/themanoj-025/Institute-Management-System/issues)
- 💡 [Request a feature](https://github.com/themanoj-025/Institute-Management-System/issues)
- 📧 Email the maintainer via the issue tracker

## License

MIT License — see [LICENSE](LICENSE).

> [!IMPORTANT] The license in this README matches the `license` field in `pyproject.toml` and the contents of the `LICENSE` file. No conflicts were found.

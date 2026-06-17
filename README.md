# OpsPilot

A full-stack IT support ticketing system with AI-assisted ticket classification, built to practice production-grade backend, frontend, and DevOps workflows end to end — not just a tutorial project.

**Live demo:** https://opspilot-sand.vercel.app  
**API docs (Swagger):** https://opspilot-pfrc.onrender.com/docs  
**Repo:** https://github.com/VATSALSHARMA1511/opspilot

---

## What it does

OpsPilot lets users create, track, and resolve support tickets with role-based access control, threaded comments, enforced status workflows, and AI-generated ticket classification powered by Groq's LLM API. It's deployed as a real, working production app.

### Features

- **Auth** — register/login with JWT access + refresh tokens; logout invalidates refresh tokens via Redis
- **Tickets** — create, list (with filters, search, pagination), update, soft-delete
- **Status workflow** — enforced state machine (`open → assigned/in_progress → resolved → closed`); invalid transitions rejected server-side
- **Assignment** — assign tickets to any active user from a dropdown; auto-transitions status to `assigned`
- **Comments** — public and internal (agent/admin-only) threaded comments per ticket
- **AI classification** — on ticket creation, Groq's `llama-3.3-70b-versatile` analyzes the title/description and returns a suggested category, priority, and one-line summary; failures degrade gracefully (ticket still creates, AI fields stay null)
- **Role-based access** — `admin`, `agent`, and `viewer` roles gate available actions
- **Dashboard** — ticket stats overview
- **Sidebar session info** — shows logged-in user's name and role, persisted across page refreshes

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | FastAPI, Python 3.11, PostgreSQL (pgvector), Redis, SQLAlchemy, Alembic, Pydantic, Groq API, Pytest |
| **Frontend** | React, Vite, Tailwind CSS v3, React Router, Axios, Lucide React |
| **Infra** | Docker (local dev), Render (API + Postgres + Redis), Vercel (frontend), GitHub Actions (CI) |

---

## Project Structure

```
opspilot/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # route handlers (auth, tickets, users, ai)
│   │   ├── core/            # config, security, dependencies
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # business logic
│   │   └── tests/           # pytest suite
│   ├── alembic/             # DB migrations
│   ├── seed.py              # seeds demo data (users, tickets, comments)
│   └── docker-compose.yml
└── frontend/
    └── src/
        ├── api/             # axios client
        ├── context/         # AuthContext (session state)
        ├── components/      # Layout, shared UI
        └── pages/           # Login, Dashboard, Tickets, TicketDetail
```

---

## API Reference

Full interactive docs at [`/docs`](https://opspilot-pfrc.onrender.com/docs). Key endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create account, returns tokens + user info |
| `POST` | `/api/v1/auth/login` | Login, returns tokens + user info |
| `POST` | `/api/v1/auth/refresh` | Exchange refresh token for new access token |
| `POST` | `/api/v1/auth/logout` | Invalidate refresh token |
| `GET` | `/api/v1/tickets` | List tickets (filters, pagination) |
| `POST` | `/api/v1/tickets` | Create ticket (triggers AI classification) |
| `GET/PUT/DELETE` | `/api/v1/tickets/{id}` | Get, update, soft-delete a ticket |
| `PATCH` | `/api/v1/tickets/{id}/status` | Change ticket status |
| `PATCH` | `/api/v1/tickets/{id}/assign` | Assign ticket to a user |
| `GET/POST` | `/api/v1/tickets/{id}/comments` | List/add comments |
| `GET` | `/api/v1/users` | List active users (for assignment dropdown) |

---

## Local Setup

**Prerequisites:** Python 3.11, Node.js, Docker Desktop running.

```powershell
# Backend
cd backend
pip install -r requirements.txt
docker-compose up -d postgres redis     # check service names in docker-compose.yml
alembic upgrade head
python seed.py                          # optional: populate demo data
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Create a `.env` file in `backend/` (check `.env.example` for all variable names):

```env
DATABASE_URL=postgresql://user:password@localhost:5432/opspilot
REDIS_URL=redis://localhost:6379
GROQ_API_KEY=your_groq_api_key
PYTHONUNBUFFERED=1
```

---

## Testing

```powershell
cd backend
pytest
```

Requires a running Postgres test database (`opspilot_test`). Start it with `docker-compose up -d postgres` before running tests locally. CI runs the full suite automatically on push via GitHub Actions.

---

## Design Notes

**AI is non-blocking.** Groq API calls are wrapped to fail silently — a model deprecation or outage never blocks ticket creation; `ai_category`, `ai_priority`, and `ai_summary` just stay null. This was a real issue encountered in production when the original model (`llama3-70b-8192`) was decommissioned mid-project.

**Session state without an extra round-trip.** The frontend stores the access token and current user profile (name, role) in `localStorage` via `AuthContext`, so the sidebar shows accurate user info immediately on page load without an extra `/me` call.

**stdout buffering on Render.** Render's log stream buffers Python output by default, making `print()` debug statements invisible. Fixed by setting `PYTHONUNBUFFERED=1` as an environment variable — worth knowing if you ever deploy a FastAPI app there.

---

## Author

**Vatsal Sharma** — B.Tech CSE, VIT Vellore.

Built as a hands-on project to practice full-stack development, deployment, and debugging real production issues (model deprecations, silent failures, session state persistence) rather than just following a tutorial.
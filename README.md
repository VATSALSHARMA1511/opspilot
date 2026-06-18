# OpsPilot

A full-stack, department-driven IT helpdesk ticketing system with AI-assisted classification, role-based access control, and a structured manager review workflow. Built as a production-grade project — deployed, tested, and debugged against real issues.

**Live demo:** https://opspilot-sand.vercel.app  
**API docs (Swagger):** https://opspilot-pfrc.onrender.com/docs  
**Repo:** https://github.com/VATSALSHARMA1511/opspilot

---

## What it does

OpsPilot replaces informal issue tracking (email chains, WhatsApp messages) with a structured workflow. Users raise tickets to specific departments, managers review and assign them to team members, and members track and resolve them. Everyone sees only what's relevant to their role.

---

## Workflow

```
User raises ticket → selects target department
        ↓
Ticket enters department queue as pending_review
        ↓
Department manager reviews → approves or rejects
        ↓
Manager assigns to a member of their department
        ↓
Member works on ticket → in_progress → resolved
        ↓
Manager closes ticket
```

---

## Features

**Core**
- Department-driven routing — tickets are raised to a specific department (IT, HR, Accounts, Security)
- Manager review stage — every ticket must be approved or rejected before work begins
- Structured assignment — managers assign only to members of their own department
- Enforced status state machine — invalid transitions rejected server-side
- Role-based visibility — members see only their assigned tickets; managers see their department; admins see everything
- Threaded comments — public and internal (manager/admin-only) comments per ticket
- Soft delete with full audit trail

**AI**
- On ticket creation, Groq's `llama-3.3-70b-versatile` analyzes the title and description and suggests category, priority, and a one-line summary
- AI is non-blocking — a Groq outage never prevents ticket creation; AI fields simply stay null

**Dashboard**
- Stat cards (total, open, in-progress, resolved)
- Tickets by status (donut chart)
- Tickets by priority (bar chart)
- Activity over last 30 days (line chart)

**Auth**
- JWT access + refresh tokens
- Refresh tokens stored and invalidated via Redis
- Session persists across page refreshes via localStorage

---

## Roles

| Role | Can do |
|---|---|
| **Member** | Raise tickets, view assigned tickets, update status on assigned tickets, comment |
| **Manager** | Everything above + see all dept tickets, approve/reject, assign to members, internal comments |
| **Admin** | Full access across all departments, soft delete |

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | FastAPI, Python 3.11, PostgreSQL (pgvector), Redis, SQLAlchemy, Alembic, Pydantic v2, Groq API, Pytest |
| **Frontend** | React, Vite, Tailwind CSS v3, React Router, Axios, Recharts, Lucide React |
| **Infra** | Docker (local dev), Render (API + Postgres + Redis), Vercel (frontend), GitHub Actions (CI) |

---

## Project Structure

```
opspilot/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers: auth, tickets, users, ai
│   │   ├── core/            # Config, security, JWT, dependencies
│   │   ├── models/          # SQLAlchemy models + enums
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic: ticket_service, ai_service
│   │   └── tests/           # Pytest suite
│   ├── alembic/             # DB migrations
│   └── seed.py              # Seeds departments, admin, managers, members, tickets
└── frontend/
    └── src/
        ├── api/             # Axios client with auth interceptor
        ├── context/         # AuthContext (JWT + user session)
        ├── components/      # Layout, shared UI
        └── pages/           # Login, Dashboard, Tickets, TicketDetail
```

---

## API Reference

Full interactive docs at [`/docs`](https://opspilot-pfrc.onrender.com/docs).

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public | Register. Body: email, password, full_name, role, department_id |
| `POST` | `/api/v1/auth/login` | Public | Login. Returns tokens + user object |
| `POST` | `/api/v1/auth/refresh` | Public | Exchange refresh token |
| `POST` | `/api/v1/auth/logout` | Bearer | Invalidate refresh token |
| `GET` | `/api/v1/tickets` | Bearer | List tickets (role-scoped, paginated, filterable) |
| `POST` | `/api/v1/tickets` | Bearer | Create ticket — triggers AI classification |
| `GET/PUT` | `/api/v1/tickets/{id}` | Bearer | Get or edit a ticket |
| `PATCH` | `/api/v1/tickets/{id}/review` | Manager | Accept or reject. Body: action, rejection_reason |
| `PATCH` | `/api/v1/tickets/{id}/assign` | Manager | Assign to dept member. Body: assignee_id |
| `PATCH` | `/api/v1/tickets/{id}/status` | Bearer | Update status — enforces state machine |
| `GET/POST` | `/api/v1/tickets/{id}/comments` | Bearer | List or add comments |
| `GET` | `/api/v1/users` | Bearer | List users (managers see own dept only) |
| `GET` | `/api/v1/departments` | Public | List all departments |

---

## Local Setup

**Prerequisites:** Python 3.11, Node.js, Docker Desktop running.

```powershell
# Backend
cd backend
pip install -r requirements.txt
docker-compose up -d postgres redis
alembic upgrade head
python seed.py          # seeds 4 departments, 1 admin, 8 managers, 16 members, 132 tickets
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

**backend/.env:**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/opspilot
REDIS_URL=redis://localhost:6379
SECRET_KEY=your_secret_key
GROQ_API_KEY=your_groq_api_key
```

**Seed credentials:**
- Admin: `admin@opspilot.com` / `admin123`
- Managers & Members: check seed.py output for generated emails / `password123`

---

## Testing

```powershell
cd backend
pytest
```

Requires a running Postgres test DB. Start with `docker-compose up -d postgres`. CI runs automatically on every push via GitHub Actions.

---

## Design Notes

**Department-first architecture.** Every ticket has a `target_department_id`. Visibility, assignment, and review permissions are all scoped to department boundaries. This was a ground-up redesign from a simpler flat ticketing system.

**AI is non-blocking.** Groq API calls are wrapped to fail silently. The model was originally `llama3-70b-8192` which was decommissioned mid-project — caught and fixed in production by debugging invisible logs on Render (`PYTHONUNBUFFERED=1`).

**State machine is server-enforced.** Status transitions are validated in `ticket_service.py`. The frontend mirrors these rules for UX but the backend rejects invalid transitions regardless.

**JWT with Redis revocation.** Refresh tokens are hashed and stored in Redis — logout immediately invalidates the token so it can't be reused even before expiry.

---

## Author

**Vatsal Sharma** — B.Tech CSE, VIT Vellore. Interning at Century Plyboards (India) Ltd.

Built to practice production full-stack development — not just writing code but deploying it, hitting real issues (model deprecations, buffered logs, schema redesigns on live systems), and fixing them.
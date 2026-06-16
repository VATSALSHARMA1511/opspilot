# OpsPilot

**OpsPilot** is an AI-powered IT ticket management system. Beyond standard helpdesk CRUD, it uses vector search and an LLM to find similar past tickets and draft resolution suggestions, so support teams resolve issues faster instead of starting from a blank page every time.

Built by Vatsal Sharma as a portfolio project.

---

## Tech stack

| Layer            | Choice                          | Why |
|------------------|----------------------------------|-----|
| API framework    | FastAPI (Python 3.11)            | Async-native, automatic OpenAPI docs, Pydantic validation |
| Database         | PostgreSQL + pgvector            | Relational data and vector embeddings in one engine |
| Cache / sessions | Redis                            | Refresh-token storage, fast key-value lookups |
| ORM / migrations | SQLAlchemy + Alembic             | Explicit, versioned schema changes |
| Auth             | JWT (python-jose) + passlib      | Stateless access tokens, hashed passwords |
| AI provider      | Groq API (Llama 3 8B)            | Low-latency, low-cost inference for suggestions |
| Containerization | Docker + docker-compose          | Reproducible dev and prod environments |
| Reverse proxy    | Nginx                            | TLS termination, static file serving, API proxying |
| CI/CD            | GitHub Actions + Railway         | Automated tests on every PR, auto-deploy on merge to `main` |

---

## Architecture

```
                              ┌──────────────────┐
                              │      Client       │
                              │  (browser / app)  │
                              └─────────┬──────────┘
                                        │  HTTPS
                                        ▼
                              ┌──────────────────┐
                              │       Nginx        │
                              │  - serves static    │
                              │    frontend          │
                              │  - proxies /api/ →   │
                              │    backend            │
                              └─────────┬──────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │   FastAPI backend   │
                              │ ┌────────────────┐ │
                              │ │ auth router      │ │
                              │ │ tickets router   │ │
                              │ │ ai router        │ │
                              │ └────────────────┘ │
                              └──────┬──────┬───────┘
                                     │      │
                       ┌─────────────┘      └─────────────┐
                       ▼                                   ▼
            ┌────────────────────┐               ┌──────────────────┐
            │   PostgreSQL +      │               │       Redis        │
            │     pgvector          │               │  - refresh tokens  │
            │  - users, tickets,    │               │  - rate limiting    │
            │    comments, audit     │               └──────────────────┘
            │    logs, embeddings      │
            └────────────────────┘
                       ▲
                       │ similarity search
                       │
            ┌────────────────────┐
            │      Groq API        │
            │  (Llama 3 8B)          │
            │  - similar tickets     │
            │  - resolution drafts    │
            └────────────────────┘
```

---

## Key engineering decisions

**FastAPI over Flask/Django.** Native async support matters here because every AI endpoint makes an outbound call to Groq — blocking workers on that I/O would tank throughput under Flask's sync-first model. FastAPI's Pydantic-based request/response validation also removes a whole class of manual serialization code that Flask would need bolted on, and Django's batteries (admin panel, ORM, templating) are mostly unused weight for an API-only service.

**PostgreSQL over MongoDB.** Tickets, users, comments, and audit logs are inherently relational — a ticket belongs to a user, has many comments, and generates many audit log rows. Postgres enforces those relationships and constraints at the database level instead of in application code. The deciding factor, though, is pgvector: it lets embeddings live in the same database and the same transaction as the relational data, instead of running a second specialized store.

**JWT over server-side sessions.** Stateless access tokens mean any backend replica can verify a request without a shared session store round-trip, which matters once this scales past one container. Refresh tokens are still tracked in Redis so they can be revoked on logout — getting most of the simplicity of JWTs without losing the ability to invalidate a session.

**pgvector over Pinecone.** Pinecone is a better choice past a few million vectors with heavy concurrent query load, but at this project's scale, running a second managed vector database alongside Postgres adds operational surface area and cost for no real benefit. pgvector keeps similarity search inside the same ACID transaction as the ticket write that created the embedding, which avoids consistency bugs where a ticket exists but its embedding doesn't (or vice versa).

**RAG over a direct LLM call.** Asking the LLM to draft a resolution with zero context produces generic, often wrong advice. Retrieving the most similar past tickets first and feeding their resolutions into the prompt grounds the suggestion in what actually worked before — closer to how a human support lead would coach a junior agent than a cold guess.

**Groq over OpenAI.** Groq's LPU inference is dramatically faster for Llama-class models at a lower cost per token, which matters for a feature that runs on every ticket view. OpenAI support is kept as an optional fallback (`OPENAI_API_KEY` in config) in case Groq has an outage or a future feature needs a model Groq doesn't serve.

---

## Local setup (5 commands)

```bash
git clone https://github.com/<your-username>/opspilot.git && cd opspilot
cp .env.example .env                 # fill in SECRET_KEY, GROQ_API_KEY, etc.
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python seed.py   # optional: load sample data
```

API docs are then available at `http://localhost:8000/docs`.

---

## API endpoints

| Method | Endpoint                              | Description                          | Auth required |
|--------|----------------------------------------|----------------------------------------|----------------|
| POST   | `/api/v1/auth/register`                 | Create a new user account               | No             |
| POST   | `/api/v1/auth/login`                    | Exchange credentials for tokens          | No             |
| POST   | `/api/v1/auth/refresh`                  | Exchange a refresh token for a new access token | No |
| POST   | `/api/v1/auth/logout`                   | Revoke the current refresh token          | Yes            |
| GET    | `/api/v1/tickets`                        | List tickets (paginated, filterable)       | Yes            |
| POST   | `/api/v1/tickets`                        | Create a ticket                            | Yes            |
| GET    | `/api/v1/tickets/{id}`                    | Get a single ticket                         | Yes            |
| PUT    | `/api/v1/tickets/{id}`                    | Update ticket fields                        | Yes            |
| PATCH  | `/api/v1/tickets/{id}/status`              | Transition ticket status (state machine)      | Yes            |
| PATCH  | `/api/v1/tickets/{id}/assign`              | Assign a ticket to an agent                    | Yes (role-gated) |
| DELETE | `/api/v1/tickets/{id}`                    | Soft-delete a ticket                            | Yes (role-gated) |
| POST   | `/api/v1/tickets/{id}/comments`            | Add a comment to a ticket                        | Yes            |
| GET    | `/api/v1/tickets/{id}/comments`            | List comments on a ticket                         | Yes            |
| GET    | `/api/v1/ai/tickets/{id}/similar`          | Find similar past tickets via vector search          | Yes            |
| GET    | `/api/v1/ai/tickets/{id}/suggestion`       | Generate an AI-drafted resolution suggestion           | Yes            |

Full interactive documentation (request/response schemas, try-it-out) is available at `/docs` once the server is running.

---

## Running tests

```bash
cd backend
pip install -r requirements.txt pytest pytest-cov httpx
pytest --cov=app --cov-report=term-missing
```

The same suite runs automatically in GitHub Actions on every push and pull request against `main` (see `.github/workflows/ci.yml`), against real Postgres + Redis service containers, and fails the build if coverage drops below 50%.

# Solution

## Architectural Decisions

### Backend

**Async-first with FastAPI + asyncpg**
I chose an async stack throughout (`asyncpg` driver, `AsyncSession`, `async_sessionmaker`) because FastAPI is built on ASGI and async I/O avoids blocking the event loop on DB calls. For a team-facing API this means better concurrency without needing extra worker processes.

**SQLAlchemy 2.0 ORM with `Mapped` annotations**
SQLAlchemy 2.0's `Mapped[T]` / `mapped_column()` style gives full type-checker coverage of model fields with zero boilerplate, and is the recommended modern approach over the legacy `Column()` API.

**JWT via `python-jose`, passwords via `bcrypt` directly**
`passlib` is effectively unmaintained and breaks with `bcrypt >= 4.1` (missing `__about__` attribute). I replaced it with a thin wrapper around `bcrypt` directly — two functions, no magic. JWTs carry `sub` (user id) and `role` so downstream middleware can do role checks without an extra DB query.

**Role-Based Access Control (RBAC)**
Two roles — `owner` and `member`:
- `owner`: full visibility and edit rights over all tasks.
- `member`: can create tasks; can only read/edit/delete tasks they created **or** are assigned to.

This is enforced in the task router helpers `_check_task_access` and `_check_task_edit`, keeping permission logic co-located with the resource.

**Data model**
Three tables: `users`, `tasks`, `task_members` (assignment join table with a unique constraint on `(task_id, user_id)`). This covers the MVP and the "task assignment" stretch goal with a clean many-to-many.

**Seeded default users at startup**
Registration is explicitly out of scope. On first boot the startup hook creates three users (`admin`/owner, `alice`/member, `bob`/member) if they don't already exist — idempotent and safe to re-run.

---

### Frontend

**React Router v6 + Axios**
Simple, well-known libraries. Axios interceptors handle token injection and automatic redirect on 401 globally — no per-request boilerplate.

**Auth flow**
Token stored in `localStorage`. On app load `AuthContext` re-validates it against `/api/users/me` so stale or revoked tokens are caught immediately.

**Component structure**
```
App.jsx            ← router + AuthProvider
pages/
  LoginPage        ← login form
  TasksPage        ← task list, filter bar, CRUD actions
components/
  Navbar           ← sticky nav with user/role badge + logout
  TaskModal        ← create / edit modal (shared)
  ProtectedRoute   ← redirects unauthenticated users to /login
context/
  AuthContext      ← user state, signIn, signOut
api.js             ← axios instance + all API calls
```

**No state management library**
React's built-in `useState` / `useEffect` / `useContext` is sufficient for this scope. Adding Redux or Zustand would be over-engineering.

---

### Docker / Production

**Multi-stage frontend build**
`node:20-alpine` builds the Vite bundle; `nginx:alpine` serves the static files. Nginx also proxies `/api/*` to the backend container so the frontend never needs CORS configuration in production — the browser only ever talks to one origin.

**Health check on Postgres**
`pg_isready` health check ensures the `api` service only starts after the DB is accepting connections, preventing startup race conditions.

---

## Trade-offs

| Decision | Trade-off |
|---|---|
| Passwords hashed with `bcrypt` directly | More control, avoids passlib's stale deps; slightly more code than `passlib.hash` |
| SQLite in-memory for tests | Fast, zero infrastructure; tests don't cover Postgres-specific behaviour (e.g. enum types) |
| `@app.on_event("startup")` for DB init | Deprecated in FastAPI ≥ 0.93 in favour of lifespan; fine for this scope, easy to migrate |
| No Alembic migrations | Tables are created with `create_all` on startup — simpler for a take-home, but not suitable for production schema changes |
| JWT expiry = 24 h | Convenient for development; production should use short-lived access tokens + refresh tokens |

---

## What I Would Improve With More Time

- **Alembic migrations** — replace `create_all` with versioned migrations for safe schema evolution
- **Refresh tokens** — short-lived JWTs (15 min) + a `/api/auth/refresh` endpoint
- **Pagination** — `GET /api/tasks` should accept `?page=` / `?limit=` for large datasets
- **Task comments** — a `comments` table linked to `tasks` + `users`; routes under `/api/tasks/{id}/comments`
- **Due-date notifications** — a background task (APScheduler / Celery) that emails assignees before due dates
- **Activity log** — an `events` table recording every create/update/delete with actor + diff
- **Input sanitisation** — strip HTML from free-text fields before storage
- **Rate limiting** — `slowapi` middleware on the login endpoint to prevent brute-force
- **E2E tests** — Playwright tests against the running Docker stack

---

## How to Run

### Full stack (Docker)

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

### Local development

```bash
# 1. Start the database
docker compose up -d db

# 2. Install backend dependencies
uv pip install -e ".[dev]"

# 3. Run the API
uvicorn src.main:app --reload

# 4. In a separate terminal, run the frontend
cd frontend
npm install
npm run dev
```

### Run tests

```bash
pytest -v
```

Tests use an in-memory SQLite database — no running Postgres required.

### Default accounts

| Username | Password | Role   |
|----------|----------|--------|
| admin    | admin123 | owner  |
| alice    | alice123 | member |
| bob      | bob123   | member |

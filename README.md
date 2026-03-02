# Task Manager API - Take-Home Assignment

## Project Brief

Build a **production-ready Task Management API with a React frontend**.

Your system should allow teams to:
- Manage tasks (create, update, track status)
- Control access based on user roles/permissions
- Authenticate users securely

---

## What to Build

### Required Features

**Must Have (MVP):**
- User authentication (login. The registration is not needed, a default user can be used)
- Task CRUD operations
- Simple role-based access (owner vs member)
- Minimal React frontend to interact with the API

**Should Have (if time permits):**
- Task filtering by status
- Task assignment to users

**Nice to Have (bonus):**
- Task comments
- Due date notifications
- Activity log
- Advanced frontend features

---

## Technical Requirements

### Backend

**Tech Stack (Required):**
- Python 3.13+
- FastAPI + Uvicorn
- SQLAlchemy
- PostgreSQL (provided in docker-compose.yml)
- pytest

**API Endpoints (Suggested Structure):**
```
Authentication:
POST   /api/auth/login

Tasks:
GET    /api/tasks          (list user's tasks)
POST   /api/tasks          (create task)
GET    /api/tasks/{id}
PUT    /api/tasks/{id}
DELETE /api/tasks/{id}
```

You can modify this structure if you have a better approach.

**Authentication:**

Implement JWT-based authentication:
- Login returns JWT token
- Protected endpoints verify JWT
- Use any library you're comfortable with (python-jose, PyJWT, etc.)

**Data Model Guidelines:**

Your system needs at minimum:
- **Users** (with authentication)
- **Tasks** (with status tracking)
- **Relationships** between users and tasks

Design the schema based on the requirements. Document your decisions.

---

### Frontend

**Tech Stack:**
- React 18+
- Vite (starter provided)
- Your choice of styling (Tailwind, Material-UI, plain CSS, etc.)

**Minimum (Required):**
- Login page
- Task list page with CRUD operations (create, update status, delete)
- Basic navigation
- API integration with authentication

**Stretch Goal (Optional):**
- Task management UI
- Task filtering and search
- User assignment interface
- Responsive design improvements

**Not Required:**
- Pixel-perfect design
- Complex animations
- State management libraries (unless you want to use them)

---

## Getting Started

We've provided:
- Docker Compose setup with PostgreSQL
- Base backend project structure
- Frontend starter with Vite + React
- Dependency management with `uv`

### Backend Setup
```bash
# Install dependencies
uv pip install -e ".[dev]"

# Start database
docker compose up -d db

# Run the API (after you implement it)
uvicorn src.main:app --reload
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

---

## What We're Looking For

### Backend (60%)
- **Functionality**: Working API with authentication and permissions
- **Code Quality**: Clean, maintainable code with proper structure
- **Testing**: Critical paths covered with meaningful tests
- **Production Readiness**: Error handling, logging, security basics
- **Architecture**: Sensible design decisions

### Frontend (30%)
- **Functionality**: Can interact with all core API features
- **Code Quality**: Clean React components
- **User Experience**: Intuitive, functional interface
- **API Integration**: Proper error handling, loading states

### Documentation (10%)
- **SOLUTION.md**: Clear explanation of your decisions
- **Code Documentation**: Comments where needed
- **Setup Instructions**

---

## Submission

1. **Create a public GitHub repository** with your solution
2. **Commit regularly** - we want to see your development process
3. **Include a SOLUTION.md** that explains:
   - Your architectural decisions
   - Trade-offs you considered
   - What you prioritized and why
   - What you would improve with more time
   - How to run and test your solution
4. **Send us the repository link** within **72 hours (3 days)**

---

## AI Usage

**AI tools are welcomed and encouraged.** We use them daily.

What matters:
- You understand the code you submit
- You can explain your design decisions
- The code quality reflects professional standards

---

## Questions & Clarifications

**We want you to succeed.** If you have questions about requirements:
- Email us at [Wazuh HR](hr@wazuh.com)
- We'll respond as soon as we can!

Don't let ambiguity block you - ask!

---

## Important Notes

### Scope Management
- **Focus on the MVP first** - make sure core features work
- **Don't over-engineer** - production-ready for a small team, not Google-scale
- **Document what you didn't implement** - explain your prioritization

### What "Production-Ready" Means
- Can be deployed and run reliably
- Has appropriate error handling
- Includes tests for critical functionality
- Is documented
- Has basic security (password hashing, JWT validation, etc.)

### Dependencies
- You can add/remove/update dependencies as needed
- **Document your changes** in SOLUTION.md with justification

---

## Definition of Done

Your submission should:
- Backend API runs with `uvicorn src.main:app --reload`
- Frontend runs with `npm run dev` (in frontend directory)
- Tests pass with `pytest`
- Database can be started with `docker compose up -d`
- README or SOLUTION.md has clear setup instructions
- Core user flows work end-to-end (register → login → create task → view task)

---

**Good luck!** 🚀

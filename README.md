# Project 3 — Advanced Agent

This project is the next step after the LLM chatbot and knowledge agent.

It demonstrates:

- Multiple tools
- Structured output
- Authentication
- Authorization
- Long-term memory
- Multi-step tasks
- PostgreSQL
- SQLAlchemy
- Gemini function calling
- JWT authentication
- React + FastAPI

## Architecture

```text
React
  |
  | JWT
  v
FastAPI
  |
  +---- PostgreSQL
  |       + users
  |       + leave_balances
  |       + leave_requests
  |       + user_memories
  |       + chats
  |       + messages
  |
  +---- Gemini Agent
          + get_profile
          + get_leave_balance
          + list_leave_requests
          + create_leave_request
          + get_memory
          + save_memory
          + approve_leave_request
          + structured final response
```

## The agent loop

```text
User
 ↓
Gemini
 ↓
Need a tool?
 ├─ No → final response
 └─ Yes
      ↓
   Python tool
      ↓
   PostgreSQL
      ↓
   tool result
      ↓
   Gemini
      ↓
   another tool OR final response
```

The model only requests tools. Python executes them. This is important because authorization must be enforced by application code, not by the LLM.

## Features

### Multiple tools

- get_profile
- get_leave_balance
- list_leave_requests
- create_leave_request
- get_memory
- save_memory
- approve_leave_request

### Structured output

The final model response is validated as:

```json
{
  "answer": "...",
  "intent": "...",
  "actions": [],
  "memory_used": [],
  "requires_confirmation": false
}
```

### Authentication

Login returns a JWT.

```text
email + password
      ↓
password verification
      ↓
JWT
      ↓
Authorization: Bearer <JWT>
```

### Authorization

Roles:

```text
employee
manager
```

Employees can access their own data and create their own leave request.

Managers can approve leave requests.

Security rule:

```text
LLM decides WHAT tool it wants
Backend decides WHETHER the user is allowed
```

The LLM never supplies the authenticated user ID.

### Long-term memory

`user_memories` stores useful preferences across chats.

Example:

```text
communication_style = concise
```

This is different from chat history.

### Multi-step tasks

Try:

```text
Check my leave balance and request leave from 2026-09-01 to 2026-09-03 for a family trip.
```

The agent should perform:

```text
get_leave_balance
       ↓
check result
       ↓
create_leave_request
       ↓
structured final response
```

Another test:

```text
Tell me my profile and my leave requests.
```

This can use multiple tools.

## Windows 11 setup

Install:

- Python 3.10+
- Node.js LTS
- Git
- Docker Desktop
- VS Code

Verify:

```powershell
py --version
python --version
node --version
npm --version
docker --version
docker compose version
```

### Start PostgreSQL

From the project root:

```powershell
docker compose up -d
```

Database:

```text
advanced_agent
```

User:

```text
agent_user
```

Password: configure POSTGRES_PASSWORD locally in the ignored backend/.env file.

### Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```env
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.6-flash
# Configure DATABASE_URL locally in the ignored backend/.env file.
JWT_SECRET=replace_with_a_long_random_secret
JWT_EXPIRE_MINUTES=60
FRONTEND_ORIGIN=http://localhost:5173
```

Seed:

```powershell
python -m scripts.seed
```

Start:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally:

```text
http://localhost:5173
```

## Demo accounts

The seed script creates two local-only example accounts:

| Role | Email | Password |
| --- | --- | --- |
| Employee | `employee@example.com` | `demo-password` |
| Manager | `manager@example.com` | `demo-password` |

These credentials are for local development only. Do not reuse them in a deployed or shared environment.

## Test cases

### Profile

```text
What is my department and job title?
```

Expected tool:

```text
get_profile
```

### Leave balance

```text
How much annual leave do I have left?
```

Expected:

```text
get_leave_balance
```

### Leave requests

```text
Show my leave requests.
```

Expected:

```text
list_leave_requests
```

### Multi-step

```text
Check my leave balance and request leave from 2026-09-01 to 2026-09-03 for a family trip.
```

Expected:

```text
get_leave_balance
        ↓
create_leave_request
```

### Memory

```text
Remember that I prefer concise answers.
```

Then start another chat:

```text
What communication style do I prefer?
```

### Authorization

Login as Demo Employee:

```text
Approve leave request 1.
```

Expected:

```text
Authorization denied
```

Login as Demo Manager:

```text
Approve leave request 1.
```

A pending request can then be approved if the balance is sufficient.

## Database inspection

```powershell
docker exec -it project3-advanced-agent-postgres psql -U agent_user -d advanced_agent
```

Then:

```sql
\dt
SELECT id,name,email,role FROM users;
SELECT * FROM leave_balances;
SELECT * FROM leave_requests;
SELECT * FROM user_memories;
SELECT * FROM chats;
SELECT * FROM messages;
```

## Gemini embeddings + RAG

This version uses Gemini embeddings again because your embedding API issue is now resolved.

The RAG path is:

```text
Company documents
      ↓
Gemini Embeddings
      ↓
pgvector
      ↓
PostgreSQL
      ↓
search_company_knowledge tool
      ↓
Gemini agent
      ↓
answer
```

The project uses:

```env
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
```

The knowledge base is stored in the `knowledge_chunks` table with a vector column.

After starting PostgreSQL and installing dependencies, run:

```powershell
python -m scripts.index_knowledge
```

This indexes the demo company documents.

Try:

```text
What is the company leave policy?
```

or:

```text
Can a manager approve leave if the employee has insufficient balance?
```

The agent should call:

```text
search_company_knowledge
```

before answering policy questions.


## File guide

```text
backend/app/config.py
    Environment variables and system prompt

backend/app/models.py
    PostgreSQL tables

backend/app/security.py
    Password hashing + JWT authentication

backend/app/tools.py
    Real business tools + authorization-sensitive operations

backend/app/agent.py
    Agent loop + tool dispatch + structured output

backend/app/main.py
    FastAPI routes

backend/scripts/seed.py
    Demo users, balances and memories

frontend/src/App.jsx
    Login, chat history, chat UI and agent metadata
```

## Production improvements

Before production add:

- Alembic migrations
- Real identity provider / refresh tokens
- Secret manager
- Rate limiting
- Audit logs
- Tool approval policies
- Idempotency keys
- Tool timeouts
- Retry with jitter
- LLM observability
- Prompt-injection defenses
- PII controls
- Evaluation
- Model routing
- Docker/cloud deployment

## Learning path

```text
PROJECT 1
LLM Chatbot
  ↓
LLM + prompt + tokens + conversation + streaming

PROJECT 2
Knowledge Agent
  ↓
RAG + embeddings + pgvector + tool calling + chat history

PROJECT 3  ← THIS PROJECT
Advanced Agent
  ↓
multiple tools
structured output
authentication
authorization
long-term memory
multi-step tasks

PROJECT 4
Production Agent
  ↓
evaluation
observability
guardrails
model routing
cost/latency optimization
Docker
cloud deployment
```
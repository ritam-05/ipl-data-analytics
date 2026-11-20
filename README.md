<div align="center">
  <h1>IPL Intelligence</h1>
  <p><strong>Historical IPL analytics, a production-minded data warehouse, and an AI research assistant.</strong></p>
  <p>
    <a href="#architecture">Architecture</a> &bull;
    <a href="#getting-started">Getting started</a> &bull;
    <a href="#data-pipeline">Data pipeline</a> &bull;
    <a href="#api">API</a>
  </p>
</div>

## Overview

IPL Intelligence is a full-stack analytics platform for exploring Indian Premier League history. It turns ball-by-ball match data into a curated warehouse, exposes analytical endpoints through FastAPI, and provides a responsive Next.js dashboard with an authenticated, natural-language AI analyst.

The project covers IPL seasons from 2008 onward, subject to the source data loaded into the warehouse.

## Highlights

- Explore season trends, player records, team performance, head-to-head matchups, venue profiles, and match extremes.
- Build analytical tables from raw ball-by-ball data using Bronze, Silver, and Gold data layers.
- Run statistical investigations, including chasing advantage and scoring-era comparisons.
- Sign up and sign in with Supabase Auth.
- Ask an AI assistant data and cricket-knowledge questions; it selects RAG, SQL, or hybrid retrieval.
- Save AI analyses and retain chat history per authenticated user.
- Keep AI-generated database access read-only with SQL validation, forbidden-keyword checks, a statement timeout, and row limits.

## Tech Stack

<p align="center">
  <a href="https://nextjs.org/" title="Next.js"><img src="https://skillicons.dev/icons?i=nextjs" width="48" height="48" alt="Next.js" /></a>
  <a href="https://react.dev/" title="React"><img src="https://skillicons.dev/icons?i=react" width="48" height="48" alt="React" /></a>
  <a href="https://www.typescriptlang.org/" title="TypeScript"><img src="https://skillicons.dev/icons?i=ts" width="48" height="48" alt="TypeScript" /></a>
  <a href="https://tailwindcss.com/" title="Tailwind CSS"><img src="https://skillicons.dev/icons?i=tailwind" width="48" height="48" alt="Tailwind CSS" /></a>
  <a href="https://www.python.org/" title="Python"><img src="https://skillicons.dev/icons?i=python" width="48" height="48" alt="Python" /></a>
  <a href="https://fastapi.tiangolo.com/" title="FastAPI"><img src="https://skillicons.dev/icons?i=fastapi" width="48" height="48" alt="FastAPI" /></a>
  <a href="https://www.postgresql.org/" title="PostgreSQL"><img src="https://skillicons.dev/icons?i=postgres" width="48" height="48" alt="PostgreSQL" /></a>
  <a href="https://supabase.com/" title="Supabase"><img src="https://skillicons.dev/icons?i=supabase" width="48" height="48" alt="Supabase" /></a>
  <a href="https://aws.amazon.com/s3/" title="Amazon S3"><img src="https://cdn.simpleicons.org/amazons3/569A31" width="48" height="48" alt="Amazon S3" /></a>
</p>

<p align="center">
  <sub>Next.js &middot; React &middot; TypeScript &middot; Tailwind CSS &middot; Recharts &middot; Python &middot; FastAPI &middot; PySpark &middot; PostgreSQL &middot; Supabase &middot; pgvector &middot; LangGraph &middot; Groq</sub>
</p>

## Architecture

```text
Cricsheet ball-by-ball data
          |
          v
Bronze (raw CSV) --> PySpark cleaning --> Silver (partitioned Parquet)
                                             |
                                             v
                                    Gold dimensions and facts
                                             |
                                             v
                              Supabase PostgreSQL + pgvector
                                  |                    |
                                  |                    +--> RAG knowledge base
                                  v
                           FastAPI analytics and AI API
                                  |
                                  v
                    Next.js dashboard, charts, and Supabase Auth
```

## Repository Layout

```text
.
|-- backend/                 # FastAPI application, analytics service, and AI agent
|   `-- app/
|       |-- agents/          # LangGraph-based RAG/Text-to-SQL workflow
|       |-- api/             # Analytics, chat, profile, and saved-analysis routes
|       |-- core/            # Supabase authentication helpers
|       `-- services/        # SQL-backed analytical queries
|-- data-engineering/        # Bronze/Silver/Gold ETL and loading utilities
|-- frontend/                # Next.js dashboard and authentication UI
|-- supabase/migrations/     # PostgreSQL schema, RLS policies, and pgvector setup
`-- requirements.txt         # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Java 17+ for local PySpark execution
- A Supabase project with Auth enabled
- A Groq API key for the AI assistant

### 1. Install dependencies

```powershell
# From the repository root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

### 2. Configure environment variables

Create a root `.env` file for the backend, ETL, and AI agent:

```env
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=your-aws-region

SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
SUPABASE_SECRET_KEY=your-supabase-secret-key
SUPABASE_DB_URL=postgresql+psycopg://...

GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-120b

# Optional: comma-separated browser origins allowed to call FastAPI
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Create `frontend/.env.local` for browser-safe configuration only:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
NEXT_PUBLIC_API_URL=http://127.0.0.1:7860
```

Never expose `SUPABASE_SECRET_KEY`, `SUPABASE_DB_URL`, or `GROQ_API_KEY` in `frontend/.env.local`.

### 3. Create the database schema

Run [001_initial_schema.sql](supabase/migrations/001_initial_schema.sql) in the Supabase SQL Editor. It creates the analytical tables, user-data tables, vector store, indexes, and row-level security policies.

### 4. Build and load the data warehouse

Place the extracted Cricsheet IPL CSV files in `data-engineering/bronze/cricsheet_raw/`, then run:

```powershell
python data-engineering/eda_initial.py
python data-engineering/etl_silver.py
python data-engineering/etl_gold.py
python data-engineering/load_to_supabase.py
python data-engineering/build_rag_kb.py
```

The generated Bronze, Silver, Gold, and log files are intentionally excluded from Git.

### 5. Run the application

In one terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --port 7860
```

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). API documentation is available at [http://127.0.0.1:7860/docs](http://127.0.0.1:7860/docs).

## Data Pipeline

| Layer | Storage | Responsibility |
| --- | --- | --- |
| Bronze | Raw CSV | Stores extracted source files without transformation. |
| Silver | Partitioned Parquet | Cleans types, fills selected nulls, standardizes renamed franchises, and normalizes split-season labels. |
| Gold | Parquet and PostgreSQL | Produces query-ready dimensions and facts for analytics, dashboards, and the AI assistant. |

The Gold model contains dimensions for seasons, teams, venues, and players; and facts for matches, batting by season, bowling by season, and venue statistics.

## AI Assistant

The assistant uses a LangGraph workflow to classify each question as RAG, SQL, or hybrid:

1. RAG queries retrieve semantically similar IPL definitions, season summaries, player records, team histories, and venue profiles from `rag_documents`.
2. SQL queries generate a single PostgreSQL `SELECT` or `WITH` statement against the Gold schema.
3. Hybrid queries combine retrieved context with verified analytical results.
4. Returned data can be represented as a chart specification and rendered in the dashboard.

Generated SQL is constrained to read-only statements and is checked before execution.

## API

All analytics endpoints require a valid Supabase Bearer token.

| Area | Example endpoints |
| --- | --- |
| Dashboard | `GET /api/analytics/overview`, `GET /api/analytics/seasons`, `GET /api/analytics/stats` |
| Players | `GET /api/analytics/players/batters`, `GET /api/analytics/players/bowlers`, `GET /api/analytics/players/consistency` |
| Teams and venues | `GET /api/analytics/teams`, `GET /api/analytics/teams/h2h`, `GET /api/analytics/venues` |
| AI and user data | `POST /api/chat`, `GET /api/chat/sessions`, `GET /api/saved-analyses`, `PUT /api/profile` |

Refer to the live OpenAPI UI at `/docs` when the backend is running for complete parameters and response contracts.

## Quality Checks

```powershell
# Frontend linting
cd frontend
npm run lint

# Data and AI verification utilities
cd ..
python data-engineering/verify_analytics.py
python data-engineering/verify_agent.py
```

## Security Notes

- Supabase Row Level Security restricts profiles, chat sessions, chat messages, and saved analyses to their owners.
- The browser uses the Supabase publishable key; privileged server-side operations use the secret key only from the backend environment.
- Database credentials and API keys belong only in ignored environment files.

## License

No license has been specified for this repository. Add one before distributing or reusing the project externally.

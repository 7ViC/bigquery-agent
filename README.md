# 🤖 AutoAnalyst — Autonomous Data Analyst Agent

> A production-ready autonomous data analyst powered by **LangGraph**, **Google BigQuery**, and **LLM (Gemini / OpenAI)**. Ask questions in plain English — the agent queries, cleans, edits, analyzes, and visualizes your data automatically.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)
![GCP](https://img.shields.io/badge/GCP-BigQuery-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🎯 What This Agent Does

| Capability | Description |
|---|---|
| **Query Data** | Converts natural language → SQL, executes on BigQuery |
| **Clean Data** | Detects nulls, duplicates, type mismatches — fixes them |
| **Edit Data** | INSERT, UPDATE, DELETE rows via plain English |
| **Analyze** | Statistical summaries, correlations, trend detection |
| **Visualize** | Auto-generates charts (bar, line, scatter, heatmap) |
| **Explain** | Every step is narrated so you understand what happened |

---

## 📁 Project Structure

```
bigquery-agent/
├── agent/
│   ├── __init__.py
│   ├── graph.py            # LangGraph state machine (the brain)
│   ├── nodes.py            # All agent nodes (query, clean, edit, analyze…)
│   ├── state.py            # Agent state definition
│   ├── tools.py            # BigQuery tool wrappers
│   ├── prompts.py          # All LLM prompt templates
│   └── utils.py            # Helpers (formatting, logging)
├── api/
│   ├── __init__.py
│   ├── main.py             # FastAPI server
│   └── schemas.py          # Request/response models
├── dashboard/
│   └── app.py              # Streamlit UI dashboard
├── config/
│   ├── settings.py         # Central configuration
│   └── logging.yaml        # Logging config
├── scripts/
│   ├── setup_gcp.sh        # One-command GCP setup
│   ├── deploy.sh           # One-command Cloud Run deploy
│   ├── seed_sample_data.py # Load sample dataset into BigQuery
│   └── run_local.sh        # Start everything locally
├── tests/
│   ├── test_agent.py       # Agent integration tests
│   └── test_tools.py       # Tool unit tests
├── .github/
│   └── workflows/
│       └── deploy.yml      # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── Makefile
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 QUICKSTART — From Zero to Running in 10 Minutes

### Prerequisites

- Python 3.11+
- A Google Cloud account (free tier works)
- `gcloud` CLI installed → https://cloud.google.com/sdk/docs/install
- Git

---

### Step 1 — Download & Unzip

```bash
# Clone or unzip the project
unzip bigquery-agent.zip -d bigquery-agent
cd bigquery-agent
```

### Step 2 — Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install all packages
pip install -r requirements.txt
```

### Step 3 — Connect to GCP

```bash
# Login to Google Cloud
gcloud auth login
gcloud auth application-default login

# Run the automated GCP setup (creates project, dataset, enables APIs)
chmod +x scripts/setup_gcp.sh
./scripts/setup_gcp.sh
```

This script will:
- Create a GCP project (or use existing)
- Enable BigQuery, Cloud Run, Artifact Registry APIs
- Create a BigQuery dataset called `autoanalyst`
- Create a service account with proper permissions
- Download the service account key to `config/service-account.json`

### Step 4 — Configure Environment

```bash
cp .env.example .env
# Edit .env with your values (the setup script prints them)
```

### Step 5 — Load Sample Data (Optional)

```bash
python scripts/seed_sample_data.py
```

### Step 6 — Run Locally

```bash
# Option A: Run everything with one command
make run

# Option B: Run components separately
# Terminal 1 — API server
make api

# Terminal 2 — Dashboard
make dashboard
```

Open http://localhost:8501 for the dashboard, or hit http://localhost:8000/docs for the API.

### Step 7 — Push to Git

```bash
git init
git add .
git commit -m "feat: autonomous data analyst agent"
git remote add origin https://github.com/YOUR_USER/bigquery-agent.git
git branch -M main
git push -u origin main
```

### Step 8 — Deploy to GCP Cloud Run

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

---

## 🧠 How the Agent Works (LangGraph Architecture)

```
┌─────────────┐
│  User Prompt │
└──────┬──────┘
       │
       ▼
┌──────────────┐    ┌───────────────┐
│   ROUTER     │───▶│  QUERY Node   │──▶ BigQuery SQL execution
│  (classifies │    └───────────────┘
│   intent)    │    ┌───────────────┐
│              │───▶│  CLEAN Node   │──▶ Null/duplicate/type fixing
│              │    └───────────────┘
│              │    ┌───────────────┐
│              │───▶│  EDIT Node    │──▶ INSERT/UPDATE/DELETE
│              │    └───────────────┘
│              │    ┌───────────────┐
│              │───▶│ ANALYZE Node  │──▶ Stats, correlations, trends
│              │    └───────────────┘
│              │    ┌───────────────┐
│              │───▶│   VIZ Node    │──▶ Chart generation
└──────────────┘    └───────────────┘
       │
       ▼
┌──────────────────┐
│  EXPLAIN Node    │──▶ Narrates what was done & why
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  Response to User│
└──────────────────┘
```

The agent uses a **state machine** pattern via LangGraph. Each node is a specialist that modifies the shared state. The router LLM call classifies the user's intent and dispatches to the right node(s) — sometimes chaining multiple (e.g., "clean the data then show me a chart of sales by region").

---

## 🔧 Configuration

All config lives in `.env`:

| Variable | Description | Example |
|---|---|---|
| `GCP_PROJECT_ID` | Your GCP project | `my-project-123` |
| `GCP_LOCATION` | Region | `us-central1` |
| `BQ_DATASET` | BigQuery dataset | `autoanalyst` |
| `LLM_PROVIDER` | `gemini` or `openai` | `gemini` |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.0-flash` |
| `OPENAI_API_KEY` | Only if using OpenAI | `sk-...` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to SA key | `config/service-account.json` |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/agent/run` | Send a prompt, get full agent response |
| `POST` | `/agent/stream` | SSE stream of agent steps |
| `GET`  | `/datasets` | List available BigQuery datasets |
| `GET`  | `/tables/{dataset}` | List tables in a dataset |
| `GET`  | `/schema/{dataset}/{table}` | Get table schema |
| `GET`  | `/health` | Health check |

---

## 🧪 Testing

```bash
make test              # Run all tests
make test-agent        # Agent integration tests only
make test-tools        # Tool unit tests only
```

---

## 📦 Makefile Commands

```bash
make install           # Install dependencies
make run               # Run API + Dashboard
make api               # Run API only
make dashboard         # Run Dashboard only
make test              # Run tests
make docker-build      # Build Docker image
make docker-run        # Run in Docker
make deploy            # Deploy to Cloud Run
make clean             # Remove caches
```

---

## License

MIT

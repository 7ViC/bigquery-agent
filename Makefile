# ============================================================
# AutoAnalyst — Makefile
# ============================================================
.PHONY: help install run api dashboard test test-agent test-tools docker-build docker-run deploy clean setup seed

# Default
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Setup ───────────────────────────────────────────────
install: ## Install all dependencies
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

setup: ## Run full GCP setup
	chmod +x scripts/setup_gcp.sh
	./scripts/setup_gcp.sh

seed: ## Load sample data into BigQuery
	python scripts/seed_sample_data.py

# ─── Run ─────────────────────────────────────────────────
run: ## Start API + Dashboard
	chmod +x scripts/run_local.sh
	./scripts/run_local.sh

api: ## Start API server only
	python -m uvicorn api.main:app --host 0.0.0.0 --port $${API_PORT:-8000} --reload

dashboard: ## Start Streamlit dashboard only
	python -m streamlit run dashboard/app.py --server.port $${DASHBOARD_PORT:-8501} --server.headless true

# ─── Testing ─────────────────────────────────────────────
test: ## Run all tests
	python -m pytest tests/ -v --tb=short

test-agent: ## Run agent integration tests
	python -m pytest tests/test_agent.py -v --tb=short

test-tools: ## Run tool unit tests
	python -m pytest tests/test_tools.py -v --tb=short

# ─── Docker ──────────────────────────────────────────────
docker-build: ## Build Docker image
	docker build -t autoanalyst:latest .

docker-run: ## Run with Docker Compose
	docker compose up --build

docker-stop: ## Stop Docker containers
	docker compose down

# ─── Deploy ──────────────────────────────────────────────
deploy: ## Deploy to Google Cloud Run
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh

# ─── Cleanup ─────────────────────────────────────────────
clean: ## Remove caches and temp files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f autoanalyst.log
	@echo "✅ Cleaned"

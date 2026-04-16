#!/usr/bin/env bash
# ============================================================
# setup_gcp.sh — One-command GCP setup for AutoAnalyst
# Creates project, enables APIs, creates dataset & service account
# ============================================================
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()   { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ─── Check prerequisites ────────────────────────────────
command -v gcloud >/dev/null 2>&1 || err "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
command -v python3 >/dev/null 2>&1 || err "Python 3 not found."

# ─── Get or create project ───────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   🤖 AutoAnalyst — GCP Setup                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || true)

if [ -n "$CURRENT_PROJECT" ]; then
    log "Current GCP project: $CURRENT_PROJECT"
    read -p "Use this project? (y/n): " USE_CURRENT
    if [[ "$USE_CURRENT" =~ ^[Yy]$ ]]; then
        PROJECT_ID="$CURRENT_PROJECT"
    else
        read -p "Enter GCP project ID (existing or new): " PROJECT_ID
    fi
else
    read -p "Enter GCP project ID (existing or new): " PROJECT_ID
fi

# Check if project exists
if gcloud projects describe "$PROJECT_ID" &>/dev/null; then
    ok "Project '$PROJECT_ID' found."
else
    log "Creating project '$PROJECT_ID'..."
    gcloud projects create "$PROJECT_ID" --name="AutoAnalyst" || err "Failed to create project."
    ok "Project created."
fi

gcloud config set project "$PROJECT_ID"

# ─── Enable billing check ───────────────────────────────
BILLING=$(gcloud beta billing projects describe "$PROJECT_ID" --format="value(billingEnabled)" 2>/dev/null || echo "false")
if [ "$BILLING" != "True" ]; then
    warn "Billing is not enabled for project '$PROJECT_ID'."
    warn "Enable it at: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    read -p "Press Enter once billing is enabled..."
fi

# ─── Enable APIs ─────────────────────────────────────────
log "Enabling required APIs..."
APIS=(
    "bigquery.googleapis.com"
    "bigquerystorage.googleapis.com"
    "run.googleapis.com"
    "artifactregistry.googleapis.com"
    "cloudbuild.googleapis.com"
    "aiplatform.googleapis.com"
)

for api in "${APIS[@]}"; do
    gcloud services enable "$api" --quiet
    ok "  ✓ $api"
done

# ─── Set region ──────────────────────────────────────────
REGION="us-central1"
read -p "GCP region [$REGION]: " INPUT_REGION
REGION="${INPUT_REGION:-$REGION}"

# ─── Create BigQuery dataset ────────────────────────────
DATASET="autoanalyst"
read -p "BigQuery dataset name [$DATASET]: " INPUT_DATASET
DATASET="${INPUT_DATASET:-$DATASET}"

if bq ls -d "$PROJECT_ID:$DATASET" &>/dev/null; then
    ok "Dataset '$DATASET' already exists."
else
    log "Creating BigQuery dataset '$DATASET'..."
    bq mk --dataset \
        --location="$REGION" \
        --description="AutoAnalyst agent data" \
        "$PROJECT_ID:$DATASET"
    ok "Dataset created."
fi

# ─── Create service account ─────────────────────────────
SA_NAME="autoanalyst-agent"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null 2>&1; then
    ok "Service account '$SA_NAME' already exists."
else
    log "Creating service account '$SA_NAME'..."
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="AutoAnalyst Agent" \
        --description="Service account for AutoAnalyst data agent"
    ok "Service account created."
fi

# Grant roles
log "Granting BigQuery permissions..."
ROLES=(
    "roles/bigquery.dataEditor"
    "roles/bigquery.jobUser"
    "roles/bigquery.user"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$role" \
        --quiet >/dev/null
    ok "  ✓ $role"
done

# ─── Download key ────────────────────────────────────────
KEY_PATH="config/service-account.json"
mkdir -p config

if [ -f "$KEY_PATH" ]; then
    warn "Service account key already exists at $KEY_PATH"
    read -p "Overwrite? (y/n): " OVERWRITE
    if [[ "$OVERWRITE" =~ ^[Yy]$ ]]; then
        gcloud iam service-accounts keys create "$KEY_PATH" \
            --iam-account="$SA_EMAIL"
        ok "New key downloaded."
    fi
else
    gcloud iam service-accounts keys create "$KEY_PATH" \
        --iam-account="$SA_EMAIL"
    ok "Service account key saved to $KEY_PATH"
fi

# ─── Create Artifact Registry repo (for Docker) ─────────
REPO_NAME="autoanalyst"
if gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" &>/dev/null 2>&1; then
    ok "Artifact Registry repo '$REPO_NAME' already exists."
else
    log "Creating Artifact Registry repository..."
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="AutoAnalyst Docker images"
    ok "Artifact Registry repo created."
fi

# ─── Write .env ──────────────────────────────────────────
log "Writing .env file..."
cat > .env << EOF
# Generated by setup_gcp.sh on $(date)
GCP_PROJECT_ID=$PROJECT_ID
GCP_LOCATION=$REGION
GOOGLE_APPLICATION_CREDENTIALS=$KEY_PATH
BQ_DATASET=$DATASET
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.0-flash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
API_HOST=0.0.0.0
API_PORT=8000
DASHBOARD_PORT=8501
LOG_LEVEL=INFO
EOF
ok ".env file created."

# ─── Summary ─────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✅ GCP Setup Complete!                     ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Project:   $PROJECT_ID"
echo "║  Region:    $REGION"
echo "║  Dataset:   $DATASET"
echo "║  SA:        $SA_EMAIL"
echo "║  Key:       $KEY_PATH"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. python scripts/seed_sample_data.py   # Load sample data"
echo "  2. make run                              # Start the agent"
echo ""

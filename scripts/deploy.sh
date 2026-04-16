#!/usr/bin/env bash
# ============================================================
# deploy.sh — One-command deploy to Google Cloud Run
# ============================================================
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[DEPLOY]${NC} $1"; }
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ─── Load config ─────────────────────────────────────────
if [ -f .env ]; then
    set -a; source .env; set +a
else
    err ".env file not found. Run scripts/setup_gcp.sh first."
fi

[ -z "${GCP_PROJECT_ID:-}" ] && err "GCP_PROJECT_ID not set in .env"
[ -z "${GCP_LOCATION:-}" ] && err "GCP_LOCATION not set in .env"

SERVICE_NAME="autoanalyst-api"
REPO_NAME="autoanalyst"
IMAGE="${GCP_LOCATION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   🚀 Deploying AutoAnalyst to Cloud Run      ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Project:  $GCP_PROJECT_ID"
echo "║  Region:   $GCP_LOCATION"
echo "║  Service:  $SERVICE_NAME"
echo "║  Image:    $IMAGE"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ─── Configure Docker auth ───────────────────────────────
log "Configuring Docker authentication..."
gcloud auth configure-docker "${GCP_LOCATION}-docker.pkg.dev" --quiet
ok "Docker auth configured."

# ─── Build ───────────────────────────────────────────────
log "Building Docker image..."
docker build -t "${IMAGE}:latest" .
ok "Image built."

# ─── Push ────────────────────────────────────────────────
log "Pushing image to Artifact Registry..."
docker push "${IMAGE}:latest"
ok "Image pushed."

# ─── Deploy to Cloud Run ────────────────────────────────
log "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image="${IMAGE}:latest" \
    --region="$GCP_LOCATION" \
    --platform=managed \
    --allow-unauthenticated \
    --port=8000 \
    --memory=1Gi \
    --cpu=2 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=120 \
    --set-env-vars="GCP_PROJECT_ID=${GCP_PROJECT_ID},GCP_LOCATION=${GCP_LOCATION},BQ_DATASET=${BQ_DATASET:-autoanalyst},LLM_PROVIDER=${LLM_PROVIDER:-gemini},GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.0-flash}" \
    --service-account="autoanalyst-agent@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --quiet

# ─── Get URL ─────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$GCP_LOCATION" \
    --format="value(status.url)")

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✅ Deployment Complete!                     ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  URL:  $SERVICE_URL"
echo "║  Docs: ${SERVICE_URL}/docs"
echo "║  Health: ${SERVICE_URL}/health"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Test it:"
echo "  curl -X POST ${SERVICE_URL}/agent/run \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"prompt\": \"Show me the top 5 sales\"}'"
echo ""

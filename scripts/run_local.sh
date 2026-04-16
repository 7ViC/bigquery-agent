#!/usr/bin/env bash
# ============================================================
# run_local.sh — Start API + Dashboard locally
# ============================================================
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${BLUE}🤖 AutoAnalyst — Starting locally...${NC}"

# Load env
if [ -f .env ]; then
    set -a; source .env; set +a
fi

API_PORT="${API_PORT:-8000}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"

# Start API in background
echo -e "${GREEN}▶ Starting API server on port $API_PORT...${NC}"
python -m uvicorn api.main:app --host 0.0.0.0 --port "$API_PORT" --reload &
API_PID=$!

# Give API a moment to start
sleep 3

# Start Streamlit
echo -e "${GREEN}▶ Starting Dashboard on port $DASHBOARD_PORT...${NC}"
python -m streamlit run dashboard/app.py --server.port "$DASHBOARD_PORT" --server.headless true &
DASH_PID=$!

echo ""
echo -e "${GREEN}✅ AutoAnalyst is running!${NC}"
echo "   API:       http://localhost:$API_PORT/docs"
echo "   Dashboard: http://localhost:$DASHBOARD_PORT"
echo ""
echo "Press Ctrl+C to stop."

# Trap SIGINT to kill both
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $API_PID 2>/dev/null || true
    kill $DASH_PID 2>/dev/null || true
    wait
    echo "Done."
}
trap cleanup SIGINT SIGTERM

# Wait for either to exit
wait

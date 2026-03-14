#!/bin/bash
# ─── Job Hunter: One command to rule them all ───
# Usage: ./run.sh          (start backend + frontend)
#        ./run.sh --scrape  (just scrape from CLI, no UI)

set -e
cd "$(dirname "$0")"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
DIM='\033[0;90m'
NC='\033[0m'

echo -e "${CYAN}◇ Job Hunter${NC}"
echo ""

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

if [ "$1" = "--scrape" ]; then
    # CLI-only scrape mode
    echo -e "${CYAN}→ Running scrapers...${NC}"
    cd scrapers && python main.py && cd ..
    echo -e "${GREEN}✓ Done${NC}"
    exit 0
fi

# Install server deps if needed
pip install fastapi uvicorn --quiet --break-system-packages 2>/dev/null || pip install fastapi uvicorn --quiet

# Initialize database
python -c "import sys; sys.path.insert(0, 'server'); from database import init_db; init_db()" 2>/dev/null

# Start FastAPI backend (port 8000)
echo -e "${CYAN}→ Starting API server on :8000...${NC}"
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# Start Vite frontend (port 5173)
echo -e "${CYAN}→ Starting dashboard on :5173...${NC}"
cd dashboard && npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}✓ Job Hunter is running!${NC}"
echo -e "  Dashboard: ${CYAN}http://localhost:5173${NC}"
echo -e "  API:       ${DIM}http://localhost:8000/docs${NC}"
echo ""
echo -e "${DIM}Press Ctrl+C to stop both servers${NC}"

# Handle Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
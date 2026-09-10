#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Video Transcriber + Slide Analyzer ==="
echo ""

# Activate venv
cd "$SCRIPT_DIR/backend"
source venv/bin/activate

# Start backend
echo "Iniciando backend..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# Open frontend
echo "Abrindo frontend..."
open "$SCRIPT_DIR/frontend/index.html" 2>/dev/null || xdg-open "$SCRIPT_DIR/frontend/index.html" 2>/dev/null

echo ""
echo "Backend rodando em: http://localhost:8000"
echo "Frontend: abra frontend/index.html no navegador"
echo ""
echo "Pressione Ctrl+C para parar"

wait $BACKEND_PID

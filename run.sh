#!/bin/bash
# ============================================
# AI E-commerce Product Scout - Process Launcher
# Runs FastAPI (port 8000) and Streamlit (port 8080)
# ============================================

set -e

echo "🚀 Starting AI E-commerce Product Scout..."

# Start FastAPI backend in the background
echo "📡 Launching FastAPI backend on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info &
FASTAPI_PID=$!

# Give FastAPI a moment to start
sleep 2

# Verify FastAPI started
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
    echo "❌ FastAPI failed to start. Exiting."
    exit 1
fi
echo "✅ FastAPI backend is running (PID: $FASTAPI_PID)"

# Start Streamlit frontend in the foreground
echo "🖥️  Launching Streamlit frontend on port 8080..."
streamlit run app.py \
    --server.port 8080 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.fileWatcherType none \
    --browser.gatherUsageStats false

# If Streamlit exits, also stop FastAPI
echo "🛑 Streamlit exited. Stopping FastAPI..."
kill $FASTAPI_PID 2>/dev/null
wait $FASTAPI_PID 2>/dev/null
echo "👋 All processes stopped."

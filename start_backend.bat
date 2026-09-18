@echo off
echo Starting Confidence-Aware RAG FastAPI Backend on http://localhost:8000 ...
set PYTHONPATH=%CD%\backend
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
pause

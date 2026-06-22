@echo off
title SQL Database Agent Server
echo =====================================================================
echo  SQL DATABASE AGENT SERVER
echo =====================================================================
echo.
echo  Configuring local environment...
echo  - Database: local SQLite database (sales.db)
echo  - LLM Provider: Google Gemini (gemini-3.5-flash)
echo.
echo  Starting server at: http://localhost:8000/
echo  (Press Ctrl+C to stop)
echo.
echo =====================================================================
echo.

cd backend
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000

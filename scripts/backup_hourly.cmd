@echo off
REM E17 — Agendar no Task Scheduler (1 h). Ajuste o caminho do Python / venv.
cd /d "%~dp0.."
python scripts\backup_sqlite_hourly.py
exit /b %ERRORLEVEL%

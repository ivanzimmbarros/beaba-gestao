@echo off
REM E17 — Agendar no Task Scheduler (semanal). Ajuste o caminho do Python / venv.
cd /d "%~dp0.."
python scripts\verify_restore_weekly.py
exit /b %ERRORLEVEL%

@echo off
REM E17 — Agendar no Task Scheduler (semanal). Ajuste o caminho do Python / venv.
REM 2026-04-12 — Governação: UI Clientes+Agendamentos consolidada (ver PAINEL).
cd /d "%~dp0.."
python scripts\verify_restore_weekly.py
exit /b %ERRORLEVEL%

@echo off
REM E17 — Agendar no Task Scheduler (1 h). Ajuste o caminho do Python / venv.
REM 2026-04-12 — Governação: legado page_clientes/page_agendamentos removido; UI em page_clientes_agendamentos.
cd /d "%~dp0.."
python scripts\backup_sqlite_hourly.py
exit /b %ERRORLEVEL%

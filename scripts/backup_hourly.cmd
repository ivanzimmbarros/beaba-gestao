@echo off
REM E17 — Agendar no Task Scheduler (1 h). Ajuste o caminho do Python / venv.
REM 2026-04-12 — Governação: legado page_clientes/page_agendamentos removido; UI em page_clientes_agendamentos.
REM CAG Setor 4 (lista no expander Agendamentos): regressão em tests/cag_setor4_ui_contract.py.
cd /d "%~dp0.."
python scripts\backup_sqlite_hourly.py
exit /b %ERRORLEVEL%

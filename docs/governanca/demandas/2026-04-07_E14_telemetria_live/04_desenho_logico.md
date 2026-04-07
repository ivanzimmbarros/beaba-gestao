# 04 — Desenho lógico

**Demanda:** `2026-04-07_E14_telemetria_live` · **2026-04-07**

- Campos opcionais no JSON; UI tolera ausência.
- `page_fluxo_gestao.py`: bloco STATUS LIVE + `streamlit-autorefresh` (10 s) quando há actividade ou demanda activa; botão **Actualizar agora**.
- Dependência: `streamlit-autorefresh` em `requirements.txt`.

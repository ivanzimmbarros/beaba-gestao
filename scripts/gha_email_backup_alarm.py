#!/usr/bin/env python3
"""
Gera texto + HTML para o e-mail de falha dos workflows backup_hourly, backup_daily e backup_weekly.

Formato: resumo visual (ícone vermelho, tipo, data/hora) antes dos detalhes técnicos.
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path


def _tier_info(tier: str) -> tuple[str, str, str]:
    t = tier.lower().strip()
    if t == "hourly":
        return (
            "Backup HOURLY",
            "backup_hourly.yml",
            "Agendamento: todas as branches (cron) ou só a branch do push.",
        )
    if t == "daily":
        return ("Backup DAILY", "backup_daily.yml", "Agendamento: matriz develop / staging / main (cron).")
    if t == "weekly":
        return ("Backup WEEKLY", "backup_weekly.yml", "Agendamento: matriz develop / staging / main (cron domingo).")
    raise ValueError(f"tier inválido: {tier}")


def build_files(*, tier: str, timestamp_utc: str, run_url: str, run_id: str) -> None:
    human, wf_file, sched_hint = _tier_info(tier)
    tier_u = tier.upper()

    banner_txt = (
        f"======================================================================\n"
        f"   FALHA   | {human.upper()}\n"
        f"======================================================================\n\n"
        f"  Tipo de operação.......: {human}\n"
        f"  Workflow (YAML).........: {wf_file}\n"
        f"  Momento do evento (UTC): {timestamp_utc}\n\n"
        f"--- Ver no GitHub (matriz) ---------------------------------------------\n"
        f"  {run_url}\n\n"
        f"  Identifique qual célula da matriz (develop / staging / main) falhou;\n"
        f"  no job reutilizável, veja o passo «Gate» ou os erros de upload/BEA1.\n\n"
        f"--- Contexto -------------------------------------------------------------\n"
        f"  {sched_hint}\n\n"
        f"--- Dados técnicos -------------------------------------------------------\n"
        f"  run_id........: {run_id}\n"
        f"  run_url.......: {run_url}\n\n"
    )

    plain_path = Path("gha_backup_fail_plain.txt")
    plain_path.write_text(banner_txt, encoding="utf-8")

    h_human = html.escape(human)
    h_wf = html.escape(wf_file)
    h_ts = html.escape(timestamp_utc)
    h_url = html.escape(run_url)
    h_rid = html.escape(run_id)
    h_hint = html.escape(sched_hint)

    html_doc = f"""<!DOCTYPE html>
<html lang="pt">
<head><meta charset="utf-8"></head>
<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;color:#1f2937;">
  <div style="background:#fef2f2;border-left:8px solid #dc2626;padding:16px 18px;margin:0 0 20px 0;border-radius:4px;">
    <div style="font-size:28px;line-height:1.2;margin-bottom:12px;"><span style="color:#dc2626;font-weight:bold;">&#128308;</span>
      <span style="vertical-align:middle;"><strong>FALHA</strong> &mdash; {h_human.upper()}</span></div>
    <table cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
      <tr><td style="color:#6b7280;">Tipo</td><td><strong>{h_human}</strong></td></tr>
      <tr><td style="color:#6b7280;">Workflow</td><td><code>{h_wf}</code></td></tr>
      <tr><td style="color:#6b7280;">Data/hora UTC</td><td><strong>{h_ts}</strong></td></tr>
      <tr><td style="color:#6b7280;">Run</td><td><a href="{h_url}" style="color:#2563eb;">Abrir no GitHub Actions</a></td></tr>
    </table>
    <p style="margin-top:14px;margin-bottom:0;color:#991b1b;font-size:14px;">
      Veja qual célula da matriz (develop / staging / main) falhou no link acima; depois expanda o job reutilizável e os passos com «Gate».
    </p>
  </div>
  <h3 style="color:#374151;margin-top:0;">Detalhes técnicos</h3>
  <ul style="line-height:1.6;color:#374151;">
    <li>{h_hint}</li>
    <li><strong>run_id:</strong> {h_rid}</li>
    <li><strong>URL:</strong> <a href="{h_url}">{h_url}</a></li>
  </ul>
</body>
</html>"""

    Path("gha_backup_fail_body.html").write_text(html_doc, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier", choices=["hourly", "daily", "weekly"], required=True)
    ap.add_argument("--ts", required=True, help="Texto já formatado UTC (ISO ou legível)")
    ap.add_argument("--run-url", required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    build_files(tier=args.tier, timestamp_utc=args.ts, run_url=args.run_url, run_id=args.run_id)


if __name__ == "__main__":
    main()

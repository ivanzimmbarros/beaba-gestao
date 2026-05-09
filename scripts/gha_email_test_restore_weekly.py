#!/usr/bin/env python3
"""
Gera texto + HTML dos e-mails de sucesso/falha do workflow test_restore_weekly.yml.

Lê variáveis de ambiente definidas pelo passo anterior no GHA — evita HTML multilinha dentro do YAML.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
from pathlib import Path


def _h(v: object) -> str:
    return html_lib.escape(str(v), quote=True)


def write_success() -> None:
    matrix_branch = os.environ["BEABA_MAIL_MATRIX_BRANCH"]
    matrix_env = os.environ["BEABA_MAIL_MATRIX_ENV"]
    utc = os.environ["BEABA_MAIL_UTC"]
    run_url = os.environ["BEABA_MAIL_RUN_URL"]
    run_id = os.environ["BEABA_MAIL_RUN_ID"]
    artifact_ref = os.environ["BEABA_MAIL_ARTIFACT_REF"]
    tier = os.environ.get("BEABA_MAIL_TIER", "")
    artifact_name = os.environ.get("BEABA_MAIL_ARTIFACT_NAME", "")
    git_short = os.environ["BEABA_MAIL_GIT_SHORT"]
    git_full = os.environ["BEABA_MAIL_GIT_FULL"]

    p = Path("restore_result.json")
    d = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    aud = d.get("restore_audit") or {}
    tc = d.get("table_counts") or {}
    pct = d.get("consistency_success_pct")

    plain = [
        "======================================================================",
        "  ✅ SUCESSO  |  Teste semanal de RESTORE (BeaBa)",
        "======================================================================",
        "",
        "  Operação.................: Teste de restore (BEA1 → SQLite)",
        "  Resultado visual.........: SUCESSO",
        f"  Branch dos dados.........: {matrix_branch}",
        f"  Branch do código.........: backup-and-restore @ {git_short}",
        f"  Tier da cascata..........: {tier or 'n/a'}",
        f"  Momento (UTC)............: {utc}",
        "",
        "  Esta célula concluiu a recuperação de prova com sucesso.",
        "",
        "--- Detalhes técnicos --------------------------------------------------",
        f"GitHub Environment.........: {matrix_env}",
        f"Run URL....................: {run_url}",
        f"Run ID.....................: {run_id}",
        "",
        "Origem dos dados:",
        f"  Ref download .............: {artifact_ref}",
        f"  Artefacto................: {artifact_name}",
        "",
        "restore_audit:",
        json.dumps(aud, ensure_ascii=False, indent=2) if aud else "  (sem bloco — ver anexo JSON)",
        "",
        "Contagens:",
        json.dumps(tc, ensure_ascii=False, indent=2),
        "",
        f"Integridade SQLite: PRAGMA={d.get('integrity_check')} | FK={d.get('foreign_key_violations')}",
        f"Consistência vs telemetria (backup-and-restore): {pct}%",
        f"Commit kit (completo)......: {git_full}",
        "",
    ]
    Path("email_ok_body.txt").write_text("\n".join(plain) + "\n", encoding="utf-8")

    aud_txt = json.dumps(aud, ensure_ascii=False, indent=2) if aud else "{}"
    tc_txt = json.dumps(tc, ensure_ascii=False, indent=2)
    html_doc = (
        "<!DOCTYPE html>\n"
        '<html lang="pt"><head><meta charset="utf-8"></head>\n'
        '<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;color:#1f2937;">\n'
        '  <div style="background:#ecfdf5;border-left:8px solid #16a34a;padding:16px 18px;margin:0 0 20px 0;border-radius:4px;">\n'
        '    <div style="font-size:28px;line-height:1.2;margin-bottom:10px;"><span style="color:#16a34a;">&#9989;</span>\n'
        '      <span style="font-weight:bold;color:#15803d;vertical-align:middle;">SUCESSO</span></div>\n'
        '    <div style="font-size:17px;margin-bottom:14px;font-weight:600;">Teste semanal de restore (BeaBa)</div>\n'
        '    <table cellpadding="6" cellspacing="0" style="border-collapse:collapse;">\n'
        '      <tr><td style="color:#6b7280;vertical-align:top;">Operação</td><td>Restore de prova (BEA1)</td></tr>\n'
        '      <tr><td style="color:#6b7280;">Resultado</td><td><strong style="color:#15803d;">SUCESSO</strong></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Branch dos dados</td><td><strong>{_h(matrix_branch)}</strong></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Código</td><td><code>backup-and-restore @ {_h(git_short)}</code></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Tier</td><td><strong>{_h(tier or "n/a")}</strong> — <code>{_h(artifact_name)}</code></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Data/hora UTC</td><td><strong>{_h(utc)}</strong></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Run</td><td><a href="{_h(run_url)}" style="color:#2563eb;">Abrir no GitHub Actions</a></td></tr>\n'
        "    </table>\n"
        "  </div>\n"
        '  <h3 style="color:#374151;margin-top:0;">Detalhes técnicos</h3>\n'
        f'  <p style="color:#6b7280;font-size:13px;">Environment: {_h(matrix_env)} · Ref download: {_h(artifact_ref)}</p>\n'
        "  <p><strong>restore_audit</strong></p>\n"
        f'  <pre style="background:#f9fafb;padding:12px;border-radius:4px;overflow:auto;font-size:12px;line-height:1.35;">{_h(aud_txt)}</pre>\n'
        "  <p><strong>Contagens</strong></p>\n"
        f'  <pre style="background:#f9fafb;padding:12px;border-radius:4px;overflow:auto;font-size:12px;line-height:1.35;">{_h(tc_txt)}</pre>\n'
        f'  <p style="color:#374151;">SQLite PRAGMA={_h(str(d.get("integrity_check")))} · FK={_h(str(d.get("foreign_key_violations")))} · '
        f"Consistência={_h(str(pct))}%</p>\n"
        "</body></html>"
    )
    Path("email_ok_body.html").write_text(html_doc, encoding="utf-8")


def write_failure() -> None:
    matrix_branch = os.environ["BEABA_MAIL_MATRIX_BRANCH"]
    matrix_env = os.environ["BEABA_MAIL_MATRIX_ENV"]
    utc = os.environ["BEABA_MAIL_UTC"]
    run_url = os.environ["BEABA_MAIL_RUN_URL"]
    run_id = os.environ["BEABA_MAIL_RUN_ID"]
    artifact_ref = os.environ["BEABA_MAIL_ARTIFACT_REF"]
    git_short = os.environ["BEABA_MAIL_GIT_SHORT"]
    git_full = os.environ["BEABA_MAIL_GIT_FULL"]
    art_ok = os.environ["BEABA_MAIL_ART_OK"]
    rst = os.environ["BEABA_MAIL_RST"]
    w_o = os.environ["BEABA_MAIL_W"]
    d_o = os.environ["BEABA_MAIL_D"]
    h_o = os.environ["BEABA_MAIL_H"]
    tier = os.environ.get("BEABA_MAIL_TIER", "")
    artifact_name = os.environ.get("BEABA_MAIL_ARTIFACT_NAME", "")

    p = Path("restore_result.json")
    extra_plain = "(ficheiro ausente)"
    extra_json_txt = "{}"
    if p.is_file():
        try:
            d_fail = json.loads(p.read_text(encoding="utf-8"))
            extra_plain = json.dumps(d_fail, ensure_ascii=False, indent=2)
            extra_json_txt = extra_plain
        except Exception:
            extra_plain = p.read_text(encoding="utf-8", errors="replace")
            extra_json_txt = extra_plain

    if art_ok == "failure":
        diag = "Sem ficheiro BEA1 após cascata weekly → daily → hourly (verifique backups na ref)."
    else:
        diag = "restore_sqlite.py ou validação falhou — ver logs do passo «Restore + validar» e JSON."

    plain = [
        "======================================================================",
        "  🔴 FALHA  |  Teste semanal de RESTORE (BeaBa)",
        "======================================================================",
        "",
        "  Operação.................: Teste de restore (BEA1)",
        "  Resultado visual.........: FALHA",
        f"  Branch dos dados.........: {matrix_branch}",
        f"  Branch do código.........: backup-and-restore @ {git_short}",
        f"  Momento (UTC)............: {utc}",
        "",
        f"  Diagnóstico..............: {diag}",
        "",
        "--- Cascata de downloads ----------------------------------------------",
        f"  weekly : {w_o}",
        f"  daily  : {d_o}",
        f"  hourly : {h_o}",
        "",
        "--- Detalhes técnicos --------------------------------------------------",
        f"GitHub Environment.........: {matrix_env}",
        f"Run URL....................: {run_url}",
        f"Run ID.....................: {run_id}",
        f"Ref download artefactos....: {artifact_ref}",
        f"Tier / artefacto (se aplicável): {tier or 'n/a'} / {artifact_name}",
        f"art_ok step................: {art_ok} | restore step: {rst}",
        f"Kit commit completo........: {git_full}",
        "",
        "--- restore_result.json (se existir) ---",
        extra_plain,
        "",
    ]
    Path("email_fail_body.txt").write_text("\n".join(plain) + "\n", encoding="utf-8")

    max_json = 120_000
    if len(extra_json_txt) > max_json:
        trunc = extra_json_txt[:max_json] + "..."
    else:
        trunc = extra_json_txt

    html_doc = (
        "<!DOCTYPE html>\n"
        '<html lang="pt"><head><meta charset="utf-8"></head>\n'
        '<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;color:#1f2937;">\n'
        '  <div style="background:#fef2f2;border-left:8px solid #dc2626;padding:16px 18px;margin:0 0 20px 0;border-radius:4px;">\n'
        '    <div style="font-size:28px;line-height:1.2;margin-bottom:10px;"><span style="color:#dc2626;font-weight:bold;">&#128308;</span>\n'
        '      <span style="font-weight:bold;color:#991b1b;vertical-align:middle;">FALHA</span></div>\n'
        '    <div style="font-size:17px;margin-bottom:14px;font-weight:600;">Teste semanal de restore (BeaBa)</div>\n'
        '    <table cellpadding="6" cellspacing="0" style="border-collapse:collapse;">\n'
        '      <tr><td style="color:#6b7280;">Resultado</td><td><strong style="color:#b91c1c;">FALHA</strong></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Branch dos dados</td><td><strong>{_h(matrix_branch)}</strong></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Código</td><td><code>backup-and-restore @ {_h(git_short)}</code></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Data/hora UTC</td><td><strong>{_h(utc)}</strong></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Run</td><td><a href="{_h(run_url)}" style="color:#2563eb;">GitHub Actions</a></td></tr>\n'
        f'      <tr><td style="color:#6b7280;vertical-align:top;">Diagnóstico</td><td>{_h(diag)}</td></tr>\n'
        "    </table>\n"
        f'    <p style="margin-top:14px;color:#991b1b;font-size:14px;"><strong>Cascata:</strong>\n'
        f'      weekly=<code>{_h(w_o)}</code> · daily=<code>{_h(d_o)}</code> · hourly=<code>{_h(h_o)}</code></p>\n'
        "  </div>\n"
        '  <h3 style="color:#374151;margin-top:0;">Detalhes técnicos</h3>\n'
        f'  <p style="color:#6b7280;font-size:13px;">Environment: {_h(matrix_env)} · Ref download: {_h(artifact_ref)} · '
        f"art_ok={_h(art_ok)} restore={_h(rst)}</p>\n"
        f'  <pre style="background:#f9fafb;padding:12px;border-radius:4px;overflow:auto;font-size:12px;max-height:480px;">{_h(trunc)}</pre>\n'
        "</body></html>"
    )
    Path("email_fail_body.html").write_text(html_doc, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["success", "failure"], required=True)
    args = ap.parse_args()
    if args.mode == "success":
        write_success()
    else:
        write_failure()


if __name__ == "__main__":
    main()

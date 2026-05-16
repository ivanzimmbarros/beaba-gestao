#!/usr/bin/env python3
"""
Gera texto + HTML dos e-mails de sucesso/falha do workflow test_restore_weekly.yml.

Lê variáveis de ambiente definidas pelo passo anterior no GHA — evita HTML multilinha dentro do YAML.
Relatórios em linguagem executiva (gestão); detalhes técnicos opcionais em bloco «Avançado».
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
from pathlib import Path


def _h(v: object) -> str:
    return html_lib.escape(str(v), quote=True)


def _integrity_status(d: dict) -> str:
    if d.get("integrity_check") == "ok":
        return "✅ ÍNTEGRO"
    return "❌ CORROMPIDO"


def _tier_display(tier: str) -> str:
    t = (tier or "").strip().lower()
    return {
        "weekly": "Backup semanal",
        "daily": "Backup diário",
        "hourly": "Backup horário",
    }.get(t, tier or "Não identificado")


def _sync_display(pct: object) -> str:
    if pct is None:
        return "Sem referência disponível"
    return f"{pct}% alinhado com o último registo do sistema"


def _advanced_plain_block(lines: list[str]) -> str:
    if not lines:
        return ""
    return "\n".join(["", "--- Detalhes avançados (equipa técnica) ---", *lines, ""])


def _advanced_html_block(inner_html: str) -> str:
    if not inner_html.strip():
        return ""
    return (
        '  <details style="margin-top:20px;border:1px solid #e5e7eb;border-radius:6px;padding:12px;">\n'
        '    <summary style="cursor:pointer;font-weight:600;color:#6b7280;">'
        "Detalhes avançados (equipa técnica)</summary>\n"
        '    <div style="display:block;margin-top:12px;font-size:13px;color:#4b5563;">\n'
        f"{inner_html}"
        "    </div>\n"
        "  </details>\n"
    )


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
    d = json.loads(p.read_text(encoding="utf-8-sig")) if p.is_file() else {}
    aud = d.get("restore_audit") or {}
    tc = d.get("table_counts") or {}
    pct = d.get("consistency_success_pct")
    integrity_label = _integrity_status(d)
    tier_label = _tier_display(tier)
    sync_label = _sync_display(pct)

    plain = [
        "======================================================================",
        "  ✅ SUCESSO  |  Verificação semanal de recuperação de dados (BeaBa)",
        "======================================================================",
        "",
        "  Operação.................: Teste automático de recuperação de dados",
        "  Resultado visual.........: SUCESSO",
        f"  Ambiente Testado.........: {matrix_branch}",
        f"  Tipo de Backup Encontrado: {tier_label}",
        f"  Data/Hora da Verificação.: {utc}",
        f"  Status de Integridade dos Dados: {integrity_label}",
        f"  Sincronia com o Sistema..: {sync_label}",
        "",
        "  A recuperação de prova foi concluída com sucesso neste ambiente.",
        "",
        f"  Relatório completo no GitHub: {run_url}",
        _advanced_plain_block(
            [
                f"GitHub Environment: {matrix_env}",
                f"Run ID: {run_id}",
                f"Ref. download: {artifact_ref}",
                f"Nome interno do artefacto: {artifact_name}",
                f"Versão do kit de teste: backup-and-restore @ {git_short}",
                f"Commit completo: {git_full}",
                "restore_audit:",
                json.dumps(aud, ensure_ascii=False, indent=2) if aud else "  (sem bloco)",
                "Contagens por tabela:",
                json.dumps(tc, ensure_ascii=False, indent=2),
            ]
        ),
    ]
    Path("email_ok_body.txt").write_text("\n".join(plain) + "\n", encoding="utf-8")

    aud_txt = json.dumps(aud, ensure_ascii=False, indent=2) if aud else "{}"
    tc_txt = json.dumps(tc, ensure_ascii=False, indent=2)
    adv_html = (
        f"<p>Environment: {_h(matrix_env)} · Ref. download: {_h(artifact_ref)}</p>"
        f"<p>Run ID: {_h(run_id)} · Artefacto: <code>{_h(artifact_name)}</code></p>"
        f"<p>Kit: <code>backup-and-restore @ {_h(git_short)}</code></p>"
        f"<p>Commit: <code>{_h(git_full)}</code></p>"
        "<p><strong>restore_audit</strong></p>"
        f'<pre style="background:#f9fafb;padding:12px;border-radius:4px;overflow:auto;font-size:12px;">'
        f"{_h(aud_txt)}</pre>"
        "<p><strong>Contagens por tabela</strong></p>"
        f'<pre style="background:#f9fafb;padding:12px;border-radius:4px;overflow:auto;font-size:12px;">'
        f"{_h(tc_txt)}</pre>"
    )

    html_doc = (
        "<!DOCTYPE html>\n"
        '<html lang="pt"><head><meta charset="utf-8"></head>\n'
        '<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;color:#1f2937;">\n'
        '  <div style="background:#ecfdf5;border-left:8px solid #16a34a;padding:16px 18px;'
        'margin:0 0 20px 0;border-radius:4px;">\n'
        '    <div style="font-size:28px;line-height:1.2;margin-bottom:10px;">'
        '<span style="color:#16a34a;">&#9989;</span> '
        '<span style="font-weight:bold;color:#15803d;vertical-align:middle;">SUCESSO</span></div>\n'
        '    <div style="font-size:17px;margin-bottom:14px;font-weight:600;">'
        "Verificação semanal de recuperação de dados (BeaBa)</div>\n"
        '    <table cellpadding="6" cellspacing="0" style="border-collapse:collapse;">\n'
        '      <tr><td style="color:#6b7280;vertical-align:top;">Operação</td>'
        "<td>Teste automático de recuperação de dados</td></tr>\n"
        '      <tr><td style="color:#6b7280;">Resultado</td>'
        '<td><strong style="color:#15803d;">SUCESSO</strong></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Ambiente Testado</td>'
        f"<td><strong>{_h(matrix_branch)}</strong></td></tr>\n"
        f'      <tr><td style="color:#6b7280;">Tipo de Backup Encontrado</td>'
        f"<td><strong>{_h(tier_label)}</strong></td></tr>\n"
        f'      <tr><td style="color:#6b7280;">Data/Hora da Verificação</td>'
        f"<td><strong>{_h(utc)}</strong></td></tr>\n"
        f'      <tr><td style="color:#6b7280;">Status de Integridade dos Dados</td>'
        f"<td><strong>{_h(integrity_label)}</strong></td></tr>\n"
        f'      <tr><td style="color:#6b7280;">Sincronia com o Sistema</td>'
        f"<td>{_h(sync_label)}</td></tr>\n"
        f'      <tr><td style="color:#6b7280;">Relatório</td>'
        f'<td><a href="{_h(run_url)}" style="color:#2563eb;">Abrir verificação no GitHub</a></td></tr>\n'
        "    </table>\n"
        "  </div>\n"
        f"{_advanced_html_block(adv_html)}"
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
            d_fail = json.loads(p.read_text(encoding="utf-8-sig"))
            extra_plain = json.dumps(d_fail, ensure_ascii=False, indent=2)
            extra_json_txt = extra_plain
        except Exception:
            extra_plain = p.read_text(encoding="utf-8", errors="replace")
            extra_json_txt = extra_plain

    if art_ok == "failure":
        diag = (
            "Não foi encontrada uma cópia de segurança válida para este ambiente. "
            "Verifique se os backups automáticos estão activos."
        )
    else:
        diag = (
            "A recuperação dos dados falhou na validação final. "
            "A equipa técnica deve analisar o relatório no GitHub."
        )

    main_alert = (
        "❌ ATENÇÃO: O teste automático de recuperação de dados falhou. "
        "O sistema pode estar em risco caso ocorra um desastre real."
    )

    plain = [
        "======================================================================",
        "  🔴 FALHA  |  Verificação semanal de recuperação de dados (BeaBa)",
        "======================================================================",
        "",
        main_alert,
        "",
        f"  Ambiente Testado.........: {matrix_branch}",
        f"  Data/Hora da Verificação.: {utc}",
        "",
        f"  O que aconteceu..........: {diag}",
        "",
        f"  Relatório completo no GitHub: {run_url}",
        _advanced_plain_block(
            [
                f"GitHub Environment: {matrix_env}",
                f"Run ID: {run_id}",
                f"Ref. download: {artifact_ref}",
                f"Tipo de backup (se aplicável): {_tier_display(tier)}",
                f"Nome interno do artefacto: {artifact_name}",
                f"Versão do kit: backup-and-restore @ {git_short}",
                f"Commit completo: {git_full}",
                f"Tentativa backup semanal: {w_o}",
                f"Tentativa backup diário: {d_o}",
                f"Tentativa backup horário: {h_o}",
                f"Localização do ficheiro: {art_ok} | Recuperação: {rst}",
                "--- restore_result.json ---",
                extra_plain,
            ]
        ),
    ]
    Path("email_fail_body.txt").write_text("\n".join(plain) + "\n", encoding="utf-8")

    max_json = 120_000
    trunc = extra_json_txt[:max_json] + ("..." if len(extra_json_txt) > max_json else "")

    adv_html = (
        f"<p>Environment: {_h(matrix_env)} · Ref. download: {_h(artifact_ref)}</p>"
        f"<p>Run ID: {_h(run_id)} · Artefacto: <code>{_h(artifact_name)}</code></p>"
        f"<p>Kit: <code>backup-and-restore @ {_h(git_short)}</code> · Commit: <code>{_h(git_full)}</code></p>"
        f"<p>Tentativas: semanal=<code>{_h(w_o)}</code> · diário=<code>{_h(d_o)}</code> · "
        f"horário=<code>{_h(h_o)}</code></p>"
        f"<p>Localização=<code>{_h(art_ok)}</code> · Recuperação=<code>{_h(rst)}</code></p>"
        f'<pre style="background:#f9fafb;padding:12px;border-radius:4px;overflow:auto;font-size:12px;'
        f'max-height:480px;">{_h(trunc)}</pre>'
    )

    html_doc = (
        "<!DOCTYPE html>\n"
        '<html lang="pt"><head><meta charset="utf-8"></head>\n'
        '<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;color:#1f2937;">\n'
        '  <div style="background:#fef2f2;border-left:8px solid #dc2626;padding:16px 18px;'
        'margin:0 0 20px 0;border-radius:4px;">\n'
        '    <div style="font-size:28px;line-height:1.2;margin-bottom:10px;">'
        '<span style="color:#dc2626;font-weight:bold;">&#128308;</span> '
        '<span style="font-weight:bold;color:#991b1b;vertical-align:middle;">FALHA</span></div>\n'
        '    <div style="font-size:17px;margin-bottom:14px;font-weight:600;">'
        "Verificação semanal de recuperação de dados (BeaBa)</div>\n"
        f'    <p style="color:#991b1b;font-size:16px;font-weight:600;margin:12px 0;">{_h(main_alert)}</p>\n'
        '    <table cellpadding="6" cellspacing="0" style="border-collapse:collapse;">\n'
        '      <tr><td style="color:#6b7280;">Resultado</td>'
        '<td><strong style="color:#b91c1c;">FALHA</strong></td></tr>\n'
        f'      <tr><td style="color:#6b7280;">Ambiente Testado</td>'
        f"<td><strong>{_h(matrix_branch)}</strong></td></tr>\n"
        f'      <tr><td style="color:#6b7280;">Data/Hora da Verificação</td>'
        f"<td><strong>{_h(utc)}</strong></td></tr>\n"
        f'      <tr><td style="color:#6b7280;vertical-align:top;">O que aconteceu</td>'
        f"<td>{_h(diag)}</td></tr>\n"
        f'      <tr><td style="color:#6b7280;">Relatório</td>'
        f'<td><a href="{_h(run_url)}" style="color:#2563eb;">Abrir verificação no GitHub</a></td></tr>\n'
        "    </table>\n"
        "  </div>\n"
        f"{_advanced_html_block(adv_html)}"
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

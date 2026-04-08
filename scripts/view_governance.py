#!/usr/bin/env python3
"""
Painel de governança no terminal (etapas, sprint %, tarefas).
Lê obrigatoriamente: docs/governanca/status_demanda.json

Cores: verde = concluído, amarelo = em andamento; pendente sem destaque forte.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_STATUS_REL = Path("docs") / "governanca" / "status_demanda.json"

# ANSI (Windows 10+ consola moderna; ver _enable_windows_ansi)
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _enable_windows_ansi() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(h, ctypes.byref(mode)) == 0:
            return
        kernel32.SetConsoleMode(h, mode.value | 0x0004)
    except Exception:
        pass


def _repo_root() -> Path:
    return Path(
        os.environ.get("BEABA_REPO_ROOT") or os.environ.get("GITHUB_WORKSPACE") or _REPO
    ).resolve()


def _load_status(repo: Path) -> dict:
    path = repo / _STATUS_REL
    if not path.is_file():
        raise FileNotFoundError(
            f"Ficheiro obrigatório em falta: {path} (execute a partir da raiz do repo ou defina BEABA_REPO_ROOT)."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _e17_label(data: dict) -> str:
    tit = str(data.get("titulo") or "")
    m = re.search(r"E17\.\d+", tit, re.I)
    if m:
        return m.group(0)
    did = str(data.get("demanda_id") or "")
    if re.search(r"E17[_-]2", did, re.I):
        return "E17.2"
    return "E17.x"


def _fase_weight(estado: str) -> float:
    e = (estado or "").strip().lower()
    if e == "feito":
        return 1.0
    if e in ("curso", "em curso", "andamento"):
        return 0.5
    return 0.0


def _sprint_progress_pct(fases: list) -> float:
    if not fases:
        return 0.0
    total_w = sum(_fase_weight(str(x.get("estado") or "")) for x in fases if isinstance(x, dict))
    return round(100.0 * total_w / len(fases), 1)


def _estado_line(estado: str, use_color: bool) -> str:
    e = (estado or "").strip().lower()
    if e == "feito":
        label = "Concluído"
        if use_color:
            return f"{_GREEN}{label}{_RESET}"
        return label
    if e in ("curso", "em curso", "andamento"):
        label = "Em andamento"
        if use_color:
            return f"{_YELLOW}{label}{_RESET}"
        return label
    label = "Pendente"
    if use_color:
        return f"{_DIM}{label}{_RESET}"
    return label


def _print_secoes_painel(data: dict, *, use_color: bool) -> None:
    b = _BOLD if use_color else ""
    r = _RESET if use_color else ""
    sec_ab = data.get("secao_epicos_em_execucao")
    sec_hi = data.get("secao_historico_epicos_concluidos")
    if not isinstance(sec_ab, dict) and not isinstance(sec_hi, dict):
        return

    print()
    print(f"{b}── Painel de demandas (layout v2) ──{r}")
    if isinstance(sec_ab, dict):
        print(str(sec_ab.get("titulo") or "[SEÇÃO: ÉPICOS EM EXECUÇÃO]"))
        itens = sec_ab.get("itens")
        if isinstance(itens, list) and itens:
            for ep in itens:
                if not isinstance(ep, dict):
                    continue
                print(
                    f"  • {ep.get('titulo', '—')} | {ep.get('demanda_id', '—')} | "
                    f"{ep.get('status_demanda', '—')} | fase {ep.get('fase_actual', '—')}"
                )
        else:
            print("  (nenhum item)")
    print()
    if isinstance(sec_hi, dict):
        print(str(sec_hi.get("titulo") or "[SEÇÃO: HISTÓRICO DE ÉPICOS CONCLUÍDOS]"))
        itens = sec_hi.get("itens")
        if isinstance(itens, list) and itens:
            for ep in itens:
                if not isinstance(ep, dict):
                    continue
                print(
                    f"  • {ep.get('data_conclusao', '—')} | {ep.get('titulo', '—')} | "
                    f"{ep.get('demanda_id', '—')} | {ep.get('status_demanda', '—')}"
                )
                refs = ep.get("refs_docs")
                if isinstance(refs, list) and refs:
                    for ref in refs:
                        print(f"      → {ref}")
        else:
            print("  (nenhum item)")
    print()


def _print_panel(data: dict, *, use_color: bool) -> None:
    _print_secoes_painel(data, use_color=use_color)
    ver = _e17_label(data)
    titulo = str(data.get("titulo") or "—")
    demanda = str(data.get("demanda_id") or "—")
    fase_atual = str(data.get("fase_actual") or data.get("fase_governanca") or "—")
    pc = str(data.get("pc_foco") or data.get("passo_referencia") or "—")
    live = str(data.get("live_status") or "—")
    live_iso = str(data.get("live_actualizado_iso") or "—")

    fases = data.get("fases_resumo")
    if not isinstance(fases, list):
        fases = []
    pct = _sprint_progress_pct(fases)

    b = _BOLD if use_color else ""
    r = _RESET if use_color else ""

    print()
    print(f"{b}══ Painel de governança — {ver} ══{r}")
    print(f"  Demanda: {demanda}")
    print(f"  Título:  {titulo}")
    print(f"  Fase actual / PC foco: {fase_atual} · {pc}")
    print(f"  Live ({live_iso}): {live}")
    print()
    print(f"{b}▶ Progresso da sprint (fases A–F): {pct}%{r}")
    print()

    print(f"{b}Etapas de governança (fluxo oficial){r}")
    for f in fases:
        if not isinstance(f, dict):
            continue
        fid = str(f.get("id") or "?")
        label = str(f.get("label") or "")
        pcs = str(f.get("pcs") or "")
        est = str(f.get("estado") or "")
        line = _estado_line(est, use_color)
        print(f"  [{fid}] {label} ({pcs})  →  {line}")
    print()

    print(f"{b}Ligação técnica: branch backup-and-restore{r}")
    print(
        f"  {_GREEN}develop{_RESET}"
        if use_color
        else "  develop",
        "— integração contínua, workflows de backup (hourly/daily/weekly), telemetria.",
    )
    print(
        (
            f"  {_YELLOW}backup-and-restore{_RESET}"
            if use_color
            else "  backup-and-restore"
        ),
        "— restore local obrigatório aqui (`scripts/restore_sqlite.py`);",
    )
    print("    CI `test_restore_weekly.yml` faz checkout desta branch para teste de restore.")
    print("  Tarefas de governança E17.2 cruzam estas duas linhas: código em develop, prova de restore na branch dedicada.")
    print()

    done = data.get("pontos_controlo_concluidos")
    if isinstance(done, list) and done:
        print(f"{b}Pontos de controlo concluídos (resumo){r}")
        for item in done[-8:]:
            pre = f"{_GREEN}✓{_RESET} " if use_color else "✓ "
            print(f"  {pre}{item}")
        if len(done) > 8:
            print(f"  {_DIM}(… {len(done) - 8} entradas anteriores){_RESET}" if use_color else f"  (… {len(done) - 8} entradas anteriores)")
        print()

    pend = data.get("etapas_pendentes")
    if isinstance(pend, list) and pend:
        print(f"{b}Tarefas / fila imediata{r}")
        for item in pend:
            pre = f"{_YELLOW}○{_RESET} " if use_color else "○ "
            print(f"  {pre}{item}")
        print()

    op = str(data.get("pendente") or "").strip()
    if op:
        print(f"{b}Pendente (operação){r}")
        print(f"  {op}")
        print()

    falha = data.get("falha")
    if falha:
        print(f"{b}Falha registada{r}")
        print(f"  {falha}")
        print()


def main(argv: list[str]) -> int:
    _utf8_stdio()
    p = argparse.ArgumentParser(description="Painel de governança (status_demanda.json)")
    p.add_argument(
        "--no-color",
        action="store_true",
        help="Desliga cores ANSI",
    )
    args = p.parse_args(argv[1:])
    use_color = not args.no_color and not os.environ.get("NO_COLOR")
    if use_color:
        _enable_windows_ansi()

    repo = _repo_root()
    try:
        data = _load_status(repo)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"JSON inválido em status_demanda.json: {exc}", file=sys.stderr)
        return 1

    _print_panel(data, use_color=use_color)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

#!/usr/bin/env python3
"""
População massiva para validação manual (clientes, colaboradores, catálogo, vendas, agendamentos).

Uso (na raiz do repositório):
  python scripts/seed_validacao_massiva.py --db data/beaba_validacao.db

Recomendado: ficheiro **dedicado** (`--db`) para não sobrescrever produção.
Para repor `data/beaba_gestao.db` em branco (destrutivo):
  python scripts/seed_validacao_massiva.py --db data/beaba_gestao.db --wipe-live-confirm

Gera tipicamente: **100** clientes (NIF PT + E.164), **20** colaboradores (habilitações 1..N serviços; cada ficha inclui
`iban_dados_bancarios` e restantes campos **Dados da Parceria** exigidos por `cadastrar_colaborador`),
**20** serviços (Sessão, Produto, Coworking, Pacote, Evento), **~300** vendas com cenários de pagamento
(integral, pendente, parcial, parcelado, multi-meios, cartão em 2 linhas, crédito loja, bónus, evento, pacote)
e **300** agendamentos (275 crédito + 25 pré-venda) com estados PRE_AGENDADO…CANCELADO repartidos no tempo
(2 meses anteriores, mês anterior, mês actual, mês seguinte).

Nota: a tabela legada `venda_pagamentos` não aceita `iban`; o seed usa `mbway`/`cartao_credito`/`dinheiro`.

Depois: `set BEABA_SQLITE_PATH=data/beaba_validacao.db` (Windows) ou export no Unix,
e `streamlit run src/app.py`.

Opcional: `--no-etl` para não correr o ETL dos dashboards.
"""

from __future__ import annotations

import argparse
import os
import random
import sqlite3
import sys
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _nif_pt_valido(indice: int) -> str:
    """Gera NIF PT de 9 dígitos com dígito de controlo correcto."""
    from src.modules.nif import validar_nif_portugal

    firsts = "1235689"
    for k in range(10_000_000):
        n = (indice * 1_000_003 + k * 17) % 10_000_000
        base8 = f"{firsts[indice % 7]}{n:07d}"
        soma = sum(int(base8[i]) * (9 - i) for i in range(8))
        resto = soma % 11
        dig = 0 if resto < 2 else 11 - resto
        cand = base8 + str(dig)
        if validar_nif_portugal(cand):
            return cand
    raise RuntimeError("Falha ao gerar NIF")


def _wipe(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=OFF")
    for table in (
        "dw_etl_run",
        "dw_cliente_kpi",
        "dw_fact_venda",
        "dw_fact_agendamento",
        "repasse_linhas",
        "agendamento_historico",
        "agendamento_colaboradores",
        "agendamentos",
        "credito_movimentos",
        "venda_recebimentos_previstos",
        "venda_pagamento_linhas",
        "venda_pagamentos",
        "venda_itens",
        "vendas",
        "colaborador_disponibilidade_regra",
        "colaborador_disponibilidade_plano",
        "colaborador_servicos",
        "colaboradores",
        "servico_evento_participantes",
        "servico_pacote_produtos",
        "servico_pacote_sessoes",
        "servicos",
        "especialidades",
        "cliente_contatos_emergencia",
        "cliente_filhos",
        "clientes",
    ):
        try:
            cur.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    cur.execute("PRAGMA foreign_keys=ON")


def _split_cents(total: int, ratios: list[int]) -> list[int]:
    s = sum(ratios)
    parts = [int(total * r // s) for r in ratios]
    diff = total - sum(parts)
    i = 0
    while diff != 0 and parts:
        parts[i % len(parts)] += 1 if diff > 0 else -1
        diff -= 1 if diff > 0 else -1
        i += 1
    return parts


def _date_in_window(rng: random.Random, start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=rng.randint(0, max(0, delta)))


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    d1 = date(year, month, 1)
    d2 = date(year, month, monthrange(year, month)[1])
    return d1, d2


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed massivo BeaBa para validação.")
    ap.add_argument(
        "--db",
        type=Path,
        default=ROOT / "data" / "beaba_validacao.db",
        help="Caminho SQLite (defeito: data/beaba_validacao.db).",
    )
    ap.add_argument(
        "--wipe-live-confirm",
        action="store_true",
        help="Obrigatório para apagar dados se --db apontar para beaba_gestao.db.",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-etl", action="store_true")
    args = ap.parse_args()
    db_path = args.db.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    live_name = (ROOT / "data" / "beaba_gestao.db").resolve()
    if db_path == live_name and not args.wipe_live_confirm:
        print(
            "Recuso apagar a base de produção habitual sem --wipe-live-confirm. "
            "Use outro --db ou confirme o risco.",
            file=sys.stderr,
        )
        return 2

    os.environ["BEABA_SQLITE_PATH"] = str(db_path)

    from src.database.connection import create_tables, get_connection
    from src.modules.agendamento import (
        alterar_status,
        associar_agendamento_pre_venda_a_item,
        cancelar_agendamento,
        criar_agendamento,
        criar_agendamento_pre_venda,
        obter_primeiro_item_venda_por_servico,
        saldo_bucket,
    )
    from src.modules.catalogo import cadastrar_evento, cadastrar_pacote, cadastrar_servico_fase1
    from src.modules.cliente import cadastrar_cliente
    from src.modules.colaborador import cadastrar_colaborador
    from src.modules.venda import calcular_totais_venda, registrar_venda

    create_tables()
    conn = get_connection()
    if not conn:
        print("Sem conexão SQLite.", file=sys.stderr)
        return 1
    conn.close()

    rng = random.Random(args.seed)
    _wipe(sqlite3.connect(str(db_path)))
    create_tables()
    # Remove serviços de exemplo de `create_tables` (nomes fixos) para ficar só o catálogo do seed.
    _cx = sqlite3.connect(str(db_path))
    _cx.execute("DELETE FROM servico_evento_participantes")
    _cx.execute("DELETE FROM servico_pacote_produtos")
    _cx.execute("DELETE FROM servico_pacote_sessoes")
    _cx.execute("DELETE FROM servicos")
    _cx.commit()
    _cx.close()

    # ——— Catálogo: 20 serviços ———
    sessao_ids: list[int] = []
    produto_ids: list[int] = []
    cowork_ids: list[int] = []
    pacote_ids: list[int] = []
    evento_ids: list[int] = []

    sess_specs = [
        ("Sessão Mat Pilates", 1.0, 45.0),
        ("Sessão Fisioterapia", 1.5, 55.0),
        ("Sessão Psicologia", 1.0, 60.0),
        ("Sessão Nutrição", 1.0, 50.0),
        ("Sessão Massagem", 1.0, 48.0),
        ("Sessão Yoga", 1.5, 40.0),
        ("Sessão Osteopatia", 1.0, 70.0),
        ("Sessão Enfermagem", 1.0, 42.0),
    ]
    for nome, dh, eur in sess_specs:
        ok, msg = cadastrar_servico_fase1(
            "Sessão",
            nome,
            f"Descritivo {nome} para validação.",
            True,
            sessao_duracao_horas=dh,
            sessao_valor_euros=eur,
        )
        assert ok, msg
        cur = sqlite3.connect(str(db_path)).cursor()
        cur.execute("SELECT id FROM servicos WHERE nome = ?", (nome,))
        sessao_ids.append(int(cur.fetchone()[0]))

    prod_specs = [
        ("Produto Creme SPF", "cosmética", "Creme solar 50ml", 18.0, "proprio", 15.0, None),
        ("Produto Óleo", "bem-estar", "Óleo massagem", 22.0, "repasse", None, 5.0),
        ("Produto Suplemento", "saúde", "Vitamina D", 12.5, "proprio", 10.0, None),
        ("Produto Chá", "alimentar", "Blend relax", 8.0, "repasse", None, 2.5),
    ]
    for nome, tipo, desc, val, orig, pct, vfix in prod_specs:
        ok, msg = cadastrar_servico_fase1(
            "Produto",
            nome,
            desc,
            True,
            produto_tipo=tipo,
            produto_descricao=desc,
            produto_valor_euros=val,
            produto_origem=orig,
            produto_repasse_pct=pct,
            produto_repasse_valor_euros=vfix,
        )
        assert ok, msg
        cur = sqlite3.connect(str(db_path)).cursor()
        cur.execute("SELECT id FROM servicos WHERE nome = ?", (nome,))
        produto_ids.append(int(cur.fetchone()[0]))

    cw_specs = [
        ("Cowork Mesa A", "Sala A", "hora", 6.0),
        ("Cowork Dia Inteiro", "Open space", "dia", 35.0),
        ("Cowork Hora Flex", "Hot desk", "hora", 5.5),
    ]
    for nome, sala, cob, eur in cw_specs:
        ok, msg = cadastrar_servico_fase1(
            "Coworking",
            nome,
            f"Coworking {nome}",
            True,
            cowork_sala_nome=sala,
            cowork_cobranca=cob,
            cowork_valor_euros=eur,
        )
        assert ok, msg
        cur = sqlite3.connect(str(db_path)).cursor()
        cur.execute("SELECT id FROM servicos WHERE nome = ?", (nome,))
        cowork_ids.append(int(cur.fetchone()[0]))

    ok, msg = cadastrar_pacote(
        "Pacote Pré-Natal 8x",
        "Pacote validação com várias sessões.",
        True,
        [(sessao_ids[0], 4, None), (sessao_ids[1], 4, None)],
        (produto_ids[0], 1),
        18.5,
        320.0,
    )
    assert ok, msg
    ok2, msg2 = cadastrar_pacote(
        "Pacote Bem-Estar Mix",
        "Segundo pacote para amplitude.",
        True,
        [(sessao_ids[2], 2, 1.0), (sessao_ids[3], 6, None)],
        None,
        22.0,
        410.0,
    )
    assert ok2, msg2
    cur = sqlite3.connect(str(db_path)).cursor()
    cur.execute("SELECT id FROM servicos WHERE natureza='Pacote' ORDER BY id")
    pacote_ids = [int(r[0]) for r in cur.fetchall()]

    # Eventos depois dos colaboradores (participantes). Colocamos placeholder e atualizamos? cadastrar_evento precisa colab.
    # Ordem: colaboradores primeiro com habilitações só em sessões/prod/cowork; depois eventos com esses colabs.

    habilitaveis = sessao_ids + produto_ids + cowork_ids
    assert len(habilitaveis) >= 8

    # ——— 20 colaboradores: alguns 1 serviço, outros vários ———
    colab_ids: list[int] = []
    colab_por_servico: dict[int, list[int]] = {sid: [] for sid in habilitaveis}

    def _linhas_para_colab(idx: int) -> list[tuple[int, float, str]]:
        d0 = (date.today() - timedelta(days=400 + idx)).isoformat()
        if idx < 8:
            sid = habilitaveis[idx]
            return [(sid, float(10 + (idx % 5) * 2 + 0.25), d0)]
        if idx < 14:
            s1 = habilitaveis[idx % len(habilitaveis)]
            s2 = habilitaveis[(idx + 3) % len(habilitaveis)]
            if s1 == s2:
                s2 = habilitaveis[(idx + 1) % len(habilitaveis)]
            return [
                (s1, 12.5 + (idx % 4), d0),
                (s2, 15.0 + (idx % 3), d0),
            ]
        s3 = habilitaveis[(idx * 7) % len(habilitaveis)]
        s4 = habilitaveis[(idx * 7 + 2) % len(habilitaveis)]
        s5 = habilitaveis[(idx * 7 + 4) % len(habilitaveis)]
        return [
            (s3, 11.0, d0),
            (s4, 13.5, d0),
            (s5, 14.0, d0),
        ]

    for i in range(20):
        linhas = _linhas_para_colab(i)
        tel = f"1198765{1000 + i:04d}"
        ok, msg = cadastrar_colaborador(
            nome=f"Colaborador Validação {i + 1:02d}",
            sexo=rng.choice(["Feminino", "Masculino", "Outro"]),
            data_nascimento=(date.today() - timedelta(days=365 * (22 + i % 20))).isoformat(),
            endereco_rua=f"Rua Seed {i}",
            endereco_numero=str(i + 1),
            endereco_complemento="",
            codigo_postal=f"{4000 + (i % 100):04d}-{(i * 11) % 1000:03d}",
            concelho="Porto",
            freguesia="Paranhos",
            distrito="Porto",
            pais="Portugal",
            email=f"colab.seed{i + 1}@validacao.beaba.local",
            nif_ou_documento=f"COL-SEED-{i:05d}",
            identificacao_internacional=True,
            numero_contato=tel,
            observacoes="Seed massivo",
            servicos_repasse=linhas,
            iban_dados_bancarios="PT50000201231234567890152",
        )
        assert ok, msg
        cur = sqlite3.connect(str(db_path)).cursor()
        cur.execute("SELECT id FROM colaboradores ORDER BY id DESC LIMIT 1")
        cid = int(cur.fetchone()[0])
        colab_ids.append(cid)
        for sid, _, _ in linhas:
            colab_por_servico.setdefault(sid, []).append(cid)

    for sid in habilitaveis:
        colab_por_servico[sid] = list(dict.fromkeys(colab_por_servico.get(sid, [])))

    def _pick_colabs(serv_id: int, n: int = 2) -> list[int]:
        pool = colab_por_servico.get(serv_id, [])
        if not pool:
            pool = colab_ids
        rng.shuffle(pool)
        return pool[: max(1, min(n, len(pool)))]

    # ——— 3 eventos (total naturezas = 8+4+3+2+3 = 20 serviços) ———
    for ei in range(3):
        c1, c2 = colab_ids[ei * 2], colab_ids[ei * 2 + 1]
        d_ev = (date.today() + timedelta(days=20 + ei * 15)).isoformat()
        ok, msg = cadastrar_evento(
            f"Evento Workshop Validação {ei + 1}",
            f"Evento para testes de UI e vendas {ei + 1}.",
            True,
            d_ev,
            f"Auditório Seed {ei + 1}",
            "Obs evento",
            "interno",
            15.0,
            35.0,
            5.0,
            [
                ("colaborador", c1, "", "percentual", 40.0, None),
                ("colaborador", c2, "", "percentual", 35.0, None),
            ],
        )
        assert ok, msg
    cur = sqlite3.connect(str(db_path)).cursor()
    cur.execute(
        "SELECT id FROM servicos WHERE natureza='Evento' ORDER BY id"
    )
    evento_ids = [int(r[0]) for r in cur.fetchall()]

    all_servico_ids = sessao_ids + produto_ids + cowork_ids + pacote_ids + evento_ids
    assert len(all_servico_ids) == 20

    # ——— 100 clientes ———
    cliente_ids: list[int] = []
    for i in range(100):
        nif = _nif_pt_valido(i + 1)
        tel = f"+35191{(2_000_000 + i * 7919) % 10**7:07d}"
        sexo = rng.choice(["Feminino", "Masculino", "Outro", "Prefiro não informar"])
        gravida: bool | None = None
        parto: str | None = None
        filhos: list = []
        tem_filhos = rng.random() < 0.35
        if tem_filhos:
            for fi in range(rng.randint(1, 3)):
                filhos.append(
                    (
                        f"Filho {fi + 1} Cli{i}",
                        rng.randint(1, 14),
                        rng.choice(["Feminino", "Masculino"]),
                    )
                )
        if sexo == "Feminino":
            gravida = rng.random() < 0.12
            if gravida:
                parto = (date.today() + timedelta(days=rng.randint(30, 240))).isoformat()
            else:
                parto = None
        else:
            gravida = None
            parto = None

        ok, msg = cadastrar_cliente(
            nome=f"Cliente Validação {i + 1:03d}",
            numero_contato=tel,
            endereco_rua=f"Avenida Dados {i}",
            endereco_numero=str(10 + i),
            endereco_complemento="",
            codigo_postal=f"{1000 + (i % 8999):04d}-{(i * 13) % 1000:03d}",
            concelho="Braga",
            freguesia="São Vicente",
            distrito="Braga",
            pais="Portugal",
            email=f"cliente.seed{i + 1}@validacao.beaba.local",
            sexo=sexo,
            tem_filhos=tem_filhos,
            filhos=filhos,
            gravida=gravida,
            data_parto_prevista=parto,
            observacoes="Seed massivo validação",
            contatos_emergencia=[
                ("Emergência", f"+35192{(3_000_000 + i * 65537) % 10**7:07d}")
            ],
            nif=nif,
            documento_identificacao_internacional=False,
            data_nascimento=f"19{60 + (i % 39):02d}-{(i % 28) + 1:02d}-15",
        )
        assert ok, msg
        cur = sqlite3.connect(str(db_path)).cursor()
        cur.execute("SELECT id FROM clientes ORDER BY id DESC LIMIT 1")
        cliente_ids.append(int(cur.fetchone()[0]))

    # Crédito loja para alguns clientes (abatimento em vendas)
    cred_cli = cliente_ids[:15]
    conn_raw = sqlite3.connect(str(db_path))
    curx = conn_raw.cursor()
    for j, cli in enumerate(cred_cli):
        curx.execute(
            """
            INSERT INTO credito_movimentos (
                cliente_id, tipo_movimento, valor_centavos, referencia_tipo, referencia_id, observacoes
            ) VALUES (?, 'AJUSTE_MANUAL', ?, 'seed_cred', ?, 'Seed validação')
            """,
            (cli, 5000 + j * 500, 900_000 + j),
        )
    conn_raw.commit()
    conn_raw.close()

    today = date.today()
    y, m = today.year, today.month
    if m == 1:
        p2y, p2m = y - 1, 11
    elif m == 2:
        p2y, p2m = y - 1, 12
    else:
        p2y, p2m = y, m - 2
    if m == 1:
        p1y, p1m = y - 1, 12
    else:
        p1y, p1m = y, m - 1
    if m == 12:
        ny, nm = y + 1, 1
    else:
        ny, nm = y, m + 1

    win_p2 = _month_bounds(p2y, p2m)
    win_p1 = _month_bounds(p1y, p1m)
    win_tm = _month_bounds(y, m)
    win_nx = _month_bounds(ny, nm)
    windows = [win_p2, win_p1, win_tm, win_nx]

    def _pick_sale_date() -> str:
        w = rng.choice(windows)
        return _date_in_window(rng, w[0], w[1]).isoformat()

    def _future_dates(n: int, base: date) -> list[str]:
        out = []
        for k in range(n):
            out.append((base + timedelta(days=14 + k * 21)).isoformat())
        return out

    # ——— 300 vendas ———
    vendas_criadas: list[tuple[int, int, str]] = []  # venda_id, cliente_id, cenário tag

    def _one_line(sid: int, q: int = 1, bonus: bool = False, evt: str | None = None, colab=None):
        d: dict = {
            "servico_id": sid,
            "quantidade": q,
            "is_bonus": bonus,
            "desconto_linha_tipo": "none",
            "desconto_linha_valor": None,
        }
        if evt:
            d["evento_preco"] = evt
        if colab is not None:
            d["colaborador_id"] = colab
        return d

    for vi in range(300):
        cli = rng.choice(cliente_ids)
        scenario = vi % 24
        obs = f"seed cenário {scenario}"
        colab_line = rng.choice(colab_ids) if rng.random() < 0.4 else None

        if scenario in (0, 1, 2, 3):
            sid = rng.choice(sessao_ids + cowork_ids)
            q = rng.randint(1, 3)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute(
                "SELECT sessao_valor_centavos, cowork_valor_centavos, natureza FROM servicos WHERE id=?",
                (sid,),
            )
            sv, cv, nat = c2.fetchone()
            conn2.close()
            unit = int((sv if str(nat) == "Sessão" else cv) or 5000)
            tot = unit * q
            # Nota: `venda_pagamentos.meio` no SQLite legado não inclui `iban`; usar mbway como proxy.
            meio = ["dinheiro", "mbway", "cartao_credito", "dinheiro"][scenario]
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=q, colab=colab_line)],
                None,
                None,
                [(meio, tot)],
                [],
                obs,
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, f"I{scenario}"))

        elif scenario == 4:
            sid = rng.choice(sessao_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT sessao_valor_centavos FROM servicos WHERE id=?", (sid,))
            unit = int(c2.fetchone()[0] or 5000)
            conn2.close()
            q = 2
            total = unit * q
            a, b = _split_cents(total, [40, 60])
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=q, colab=colab_line)],
                None,
                None,
                [("dinheiro", a), ("mbway", b)],
                [],
                obs + " split 40/60",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "I_split"))

        elif scenario == 5:
            sid = rng.choice(sessao_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT sessao_valor_centavos FROM servicos WHERE id=?", (sid,))
            unit = int(c2.fetchone()[0] or 5000)
            conn2.close()
            total = unit * 2
            a, b = _split_cents(total, [1, 1])
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=2, colab=colab_line)],
                None,
                None,
                [("cartao_credito", a), ("cartao_credito", b)],
                [],
                obs + " cartão 2x",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "I_cc2"))

        elif scenario == 6:
            sid = rng.choice(sessao_ids + produto_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute(
                "SELECT sessao_valor_centavos, produto_valor_centavos, natureza FROM servicos WHERE id=?",
                (sid,),
            )
            r = c2.fetchone()
            conn2.close()
            nat = str(r[2])
            unit = int((r[0] if nat == "Sessão" else r[1]) or 4000)
            total = unit
            x, y, z = _split_cents(total, [1, 1, 1])
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=1, colab=colab_line)],
                None,
                None,
                [("dinheiro", x), ("cartao_credito", y), ("mbway", z)],
                [],
                obs + " 3 meios",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "I_3m"))

        elif scenario == 7:
            sid = rng.choice(evento_ids)
            ev = rng.choice(["adulto", "crianca"])
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute(
                "SELECT evento_preco_adulto_centavos, evento_preco_crianca_centavos FROM servicos WHERE id=?",
                (sid,),
            )
            ca, cc = c2.fetchone()
            conn2.close()
            unit_ev = int(ca if ev == "adulto" else cc)
            qev = rng.randint(1, 2)
            total = unit_ev * qev
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=qev, evt=ev, colab=colab_line)],
                None,
                None,
                [("mbway", total)],
                [],
                obs + f" evento {ev}",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "I_evt"))

        elif scenario == 8:
            sid = rng.choice(pacote_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT pacote_valor_venda_centavos FROM servicos WHERE id=?", (sid,))
            total = int(c2.fetchone()[0])
            conn2.close()
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=1, colab=colab_line)],
                None,
                None,
                [("mbway", total)],
                [],
                obs + " pacote",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "I_pac"))

        elif scenario == 9:
            sid = rng.choice(sessao_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT sessao_valor_centavos FROM servicos WHERE id=?", (sid,))
            unit = int(c2.fetchone()[0] or 5000)
            conn2.close()
            total = unit
            d1 = _future_dates(1, today)[0]
            ok, msg, vid = registrar_venda(
                cli,
                "pendente",
                [_one_line(sid, q=1, colab=colab_line)],
                None,
                None,
                [],
                [(d1, total)],
                obs + " pendente",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "Pend"))

        elif scenario == 10:
            sid = rng.choice(sessao_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT sessao_valor_centavos FROM servicos WHERE id=?", (sid,))
            unit = int(c2.fetchone()[0] or 5000)
            conn2.close()
            total = unit * 2
            fds = _future_dates(2, today)
            h1, h2 = _split_cents(total, [1, 1])
            ok, msg, vid = registrar_venda(
                cli,
                "pendente",
                [_one_line(sid, q=2, colab=colab_line)],
                None,
                None,
                [],
                [(fds[0], h1), (fds[1], h2)],
                obs + " pendente 2x",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "Pend2"))

        elif scenario == 11:
            sid = rng.choice(sessao_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT sessao_valor_centavos FROM servicos WHERE id=?", (sid,))
            unit = int(c2.fetchone()[0] or 5000)
            conn2.close()
            total = unit
            p1, p2 = _split_cents(total, [35, 65])
            fd = _future_dates(1, today)[0]
            ok, msg, vid = registrar_venda(
                cli,
                "parcial",
                [_one_line(sid, q=1, colab=colab_line)],
                None,
                None,
                [("dinheiro", p1)],
                [(fd, p2)],
                obs + " parcial",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "Parc"))

        elif scenario in (12, 13):
            sid = rng.choice(sessao_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT sessao_valor_centavos FROM servicos WHERE id=?", (sid,))
            unit = int(c2.fetchone()[0] or 5000)
            conn2.close()
            total = unit * 2
            fds = _future_dates(3, today)
            thirds = _split_cents(total, [1, 1, 1])
            if scenario == 12:
                p0, p1 = _split_cents(thirds[0], [1, 1])
                ok, msg, vid = registrar_venda(
                    cli,
                    "parcelado",
                    [_one_line(sid, q=2, colab=colab_line)],
                    None,
                    None,
                    [("cartao_credito", p0), ("mbway", p1)],
                    [(fds[0], thirds[1]), (fds[1], thirds[2])],
                    obs + " parc entrada+2",
                )
            else:
                ok, msg, vid = registrar_venda(
                    cli,
                    "parcelado",
                    [_one_line(sid, q=2, colab=colab_line)],
                    None,
                    None,
                    [],
                    [(fds[0], thirds[0]), (fds[1], thirds[1]), (fds[2], thirds[2])],
                    obs + " parc 3 futuras",
                )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "ParcN"))

        elif scenario == 14 and cli in cred_cli:
            sid = rng.choice(sessao_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT sessao_valor_centavos FROM servicos WHERE id=?", (sid,))
            unit = int(c2.fetchone()[0] or 5000)
            conn2.close()
            cab = min(2500, max(0, unit - 1000))
            liq = unit - cab
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=1, colab=colab_line)],
                None,
                None,
                [("dinheiro", liq)],
                [],
                obs + " crédito",
                credito_abatido_centavos=cab,
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "Cred"))

        elif scenario == 15:
            sid = rng.choice(sessao_ids)
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=1, bonus=True, colab=colab_line)],
                None,
                None,
                [],
                [],
                obs + " bónus",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "Bonus"))

        elif scenario == 16:
            sid = rng.choice(sessao_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT sessao_valor_centavos FROM servicos WHERE id=?", (sid,))
            u = int(c2.fetchone()[0] or 5000)
            conn2.close()
            ok_t, _, totais = calcular_totais_venda(
                [
                    {
                        "quantidade": 2,
                        "preco_unitario_centavos": u,
                        "desconto_linha_tipo": "percent",
                        "desconto_linha_valor": 500,
                    }
                ],
                desconto_global_tipo="percent",
                desconto_global_valor=300,
            )
            assert ok_t
            tot = int(totais["total_final_centavos"])
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [
                    _one_line(sid, q=2, colab=colab_line)
                    | {"desconto_linha_tipo": "percent", "desconto_linha_valor": 5.0}
                ],
                "percent",
                300,
                [("mbway", tot)],
                [],
                obs + " desc linha+global",
            )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "Desc"))

        else:
            # fallback simples integral
            sid = rng.choice(sessao_ids)
            conn2 = sqlite3.connect(str(db_path))
            c2 = conn2.cursor()
            c2.execute("SELECT sessao_valor_centavos FROM servicos WHERE id=?", (sid,))
            unit = int(c2.fetchone()[0] or 5000)
            conn2.close()
            ok, msg, vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=rng.randint(1, 4), colab=colab_line)],
                None,
                None,
                [("dinheiro", unit * 2)],
                [],
                obs + " fb",
            )
            if not ok:
                ok, msg, vid = registrar_venda(
                    cli,
                    "integral",
                    [_one_line(sid, q=1, colab=colab_line)],
                    None,
                    None,
                    [("dinheiro", unit)],
                    [],
                    obs + " fb2",
                )
            assert ok, msg
            vendas_criadas.append((int(vid), cli, "Fb"))

    # ——— Reservar algumas vendas “atraso”: parcial com data prevista no passado ———
    conn_fix = sqlite3.connect(str(db_path))
    cf = conn_fix.cursor()
    cf.execute(
        """
        SELECT v.id FROM vendas v
        JOIN venda_recebimentos_previstos rp ON rp.venda_id = v.id
        WHERE v.estado_pagamento IN ('pendente','parcial','parcelado')
        LIMIT 40
        """
    )
    for (vid,) in cf.fetchall():
        past = (today - timedelta(days=rng.randint(5, 40))).isoformat()
        cf.execute(
            "UPDATE venda_recebimentos_previstos SET data_prevista = ? WHERE venda_id = ? AND ordem = 1",
            (past, vid),
        )
    conn_fix.commit()
    conn_fix.close()

    # ——— Pré-vendas + associações ———
    pre_ag_ids: list[int] = []
    for _ in range(25):
        cli = rng.choice(cliente_ids)
        sid = rng.choice(sessao_ids + cowork_ids + evento_ids[:2])
        d_ag = _date_in_window(rng, win_tm[0], win_nx[1]).isoformat()
        cols = _pick_colabs(sid, 2)
        use_pref = rng.random() < 0.3
        pr = 4500 if use_pref else None
        h0 = 9 + rng.randint(0, 5)
        ok, msg = criar_agendamento_pre_venda(
            cli,
            sid,
            d_ag,
            f"{h0:02d}:00",
            f"{h0 + 1:02d}:30",
            cols,
            "Pré-venda seed",
            preco_referencia_centavos=pr,
        )
        assert ok, msg
        conn2 = sqlite3.connect(str(db_path))
        c2 = conn2.cursor()
        c2.execute("SELECT id FROM agendamentos WHERE modo_origem='pre_venda' ORDER BY id DESC LIMIT 1")
        aid = int(c2.fetchone()[0])
        conn2.close()
        pre_ag_ids.append(aid)
        if rng.random() < 0.5:
            cq = sqlite3.connect(str(db_path)).cursor()
            if sid in evento_ids:
                evp = "adulto"
                cq.execute(
                    "SELECT evento_preco_adulto_centavos FROM servicos WHERE id=?",
                    (sid,),
                )
                total_pv = int(cq.fetchone()[0])
            else:
                evp = None
                cq.execute(
                    "SELECT sessao_valor_centavos, cowork_valor_centavos, natureza FROM servicos WHERE id=?",
                    (sid,),
                )
                sv, cv, nat = cq.fetchone()
                total_pv = int((sv if str(nat) == "Sessão" else cv) or 5000)
            ok2, msg2, new_vid = registrar_venda(
                cli,
                "integral",
                [_one_line(sid, q=1, evt=evp)],
                None,
                None,
                [("dinheiro", total_pv)],
                [],
                "Fecho pré-venda seed",
            )
            if ok2 and new_vid:
                viid = obter_primeiro_item_venda_por_servico(int(new_vid), sid)
                if viid:
                    associar_agendamento_pre_venda_a_item(aid, viid)

    # ——— 275 agendamentos crédito-venda + 25 pré-venda = 300 no total ———
    conn3 = sqlite3.connect(str(db_path))
    c3 = conn3.cursor()
    c3.execute(
        """
        SELECT vi.id, vi.servico_id, s.natureza, v.cliente_id
        FROM venda_itens vi
        JOIN vendas v ON v.id = vi.venda_id
        JOIN servicos s ON s.id = vi.servico_id
        WHERE s.natureza IN ('Sessão','Coworking','Evento','Pacote')
        """
    )
    rows_buckets = list(c3.fetchall())
    conn3.close()

    def _pacote_sessoes(pac_sid: int) -> list[int]:
        cx = sqlite3.connect(str(db_path)).cursor()
        cx.execute(
            "SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id=? ORDER BY ordem",
            (pac_sid,),
        )
        out = [int(r[0]) for r in cx.fetchall()]
        return out

    ag_ids: list[int] = []
    attempts = 0
    while len(ag_ids) < 275 and attempts < 8000:
        attempts += 1
        rng.shuffle(rows_buckets)
        picked = None
        cx = sqlite3.connect(str(db_path))
        cur = cx.cursor()
        for vi_id, serv_id, nat, cli_id in rows_buckets:
            if nat == "Pacote":
                for psid in _pacote_sessoes(serv_id):
                    sb = saldo_bucket(cur, int(vi_id), psid)
                    if sb > 0:
                        picked = (vi_id, serv_id, nat, cli_id, psid)
                        break
            else:
                sb = saldo_bucket(cur, int(vi_id), None)
                if sb > 0:
                    picked = (vi_id, serv_id, nat, cli_id, None)
                    break
        cx.close()
        if not picked:
            break
        vi_id, serv_id, nat, cli_id, psid = picked
        occ_serv = serv_id
        if nat == "Pacote" and psid is not None:
            cur = sqlite3.connect(str(db_path)).cursor()
            cur.execute(
                "SELECT sessao_servico_id FROM servico_pacote_sessoes WHERE id=?",
                (psid,),
            )
            occ_serv = int(cur.fetchone()[0])
        cols = _pick_colabs(occ_serv, rng.randint(1, 2))
        w = rng.choice(windows)
        d_ag = _date_in_window(rng, w[0], w[1]).isoformat()
        h0 = 8 + rng.randint(0, 7)
        hi = f"{h0:02d}:{rng.choice(['00', '15', '30'])}"
        hf = f"{h0 + 1:02d}:{rng.choice(['00', '15', '30'])}"
        ok, msg = criar_agendamento(
            int(vi_id),
            int(psid) if psid is not None else None,
            d_ag,
            hi,
            hf,
            cols,
            f"Ag seed #{len(ag_ids)}",
        )
        if not ok:
            continue
        conn2 = sqlite3.connect(str(db_path))
        c2 = conn2.cursor()
        c2.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
        aid = int(c2.fetchone()[0])
        conn2.close()
        ag_ids.append(aid)

    # ——— Distribuir estados ———
    status_targets = (
        ["PRE_AGENDADO"] * 25
        + ["AGENDADO"] * 45
        + ["CONFIRMADO"] * 50
        + ["REALIZADO_PENDENTE_PGTO"] * 55
        + ["CONCLUIDO"] * 85
        + ["CANCELADO"] * 40
    )
    rng.shuffle(status_targets)
    # preenche até len(ag_ids)
    while len(status_targets) < len(ag_ids):
        status_targets.append(rng.choice(["AGENDADO", "CONFIRMADO", "CONCLUIDO"]))
    status_targets = status_targets[: len(ag_ids)]

    def _liquido_venda(cx: sqlite3.Cursor, vid: int) -> tuple[int, int]:
        cx.execute(
            "SELECT total_final_centavos, COALESCE(credito_abatido_centavos, 0) FROM vendas WHERE id=?",
            (vid,),
        )
        tf, cab = cx.fetchone()
        return int(tf), int(cab)

    def _ensure_venda_pago_integral(cx: sqlite3.Cursor, vid: int) -> None:
        tf, cab = _liquido_venda(cx, vid)
        liq = max(0, tf - cab)
        cx.execute("DELETE FROM venda_recebimentos_previstos WHERE venda_id=?", (vid,))
        cx.execute("DELETE FROM venda_pagamentos WHERE venda_id=?", (vid,))
        cx.execute("DELETE FROM venda_pagamento_linhas WHERE venda_id=?", (vid,))
        cx.execute("UPDATE vendas SET estado_pagamento='integral' WHERE id=?", (vid,))
        if liq > 0:
            cx.execute(
                "INSERT INTO venda_pagamentos (venda_id, ordem, meio, valor_centavos) VALUES (?,?,?,?)",
                (vid, 1, "dinheiro", liq),
            )
            cx.execute(
                "INSERT INTO venda_pagamento_linhas (venda_id, ordem, tipo_meio, valor_centavos) VALUES (?,?,?,?)",
                (vid, 1, "DINHEIRO_MBWAY", liq),
            )

    def _ensure_venda_pago_parcial(cx: sqlite3.Cursor, vid: int) -> None:
        tf, cab = _liquido_venda(cx, vid)
        liq = max(0, tf - cab)
        if liq <= 1:
            return
        pago = max(1, liq // 3)
        resto = liq - pago
        cx.execute("DELETE FROM venda_recebimentos_previstos WHERE venda_id=?", (vid,))
        cx.execute("DELETE FROM venda_pagamentos WHERE venda_id=?", (vid,))
        cx.execute("DELETE FROM venda_pagamento_linhas WHERE venda_id=?", (vid,))
        cx.execute("UPDATE vendas SET estado_pagamento='parcial' WHERE id=?", (vid,))
        cx.execute(
            "INSERT INTO venda_pagamentos (venda_id, ordem, meio, valor_centavos) VALUES (?,?,?,?)",
            (vid, 1, "mbway", pago),
        )
        cx.execute(
            "INSERT INTO venda_pagamento_linhas (venda_id, ordem, tipo_meio, valor_centavos) VALUES (?,?,?,?)",
            (vid, 1, "DINHEIRO_MBWAY", pago),
        )
        cx.execute(
            "INSERT INTO venda_recebimentos_previstos (venda_id, ordem, data_prevista, valor_centavos) VALUES (?,?,?,?)",
            (vid, 1, (today + timedelta(days=90)).isoformat(), resto),
        )

    conn4 = sqlite3.connect(str(db_path))
    c4 = conn4.cursor()
    for aid, st in zip(ag_ids, status_targets):
        c4.execute("SELECT modo_origem, venda_id FROM agendamentos WHERE id=?", (aid,))
        row = c4.fetchone()
        modo, vid = str(row[0]), row[1]

        if st == "PRE_AGENDADO":
            c4.execute(
                "UPDATE agendamentos SET status='PRE_AGENDADO', data_alteracao=CURRENT_TIMESTAMP WHERE id=?",
                (aid,),
            )
            continue

        if st == "CANCELADO":
            conn4.commit()
            conn4.close()
            cancelar_agendamento(aid, devolver_ao_buffer=rng.choice([True, False]))
            conn4 = sqlite3.connect(str(db_path))
            c4 = conn4.cursor()
            continue

        if modo == "credito_venda" and vid:
            if st == "CONCLUIDO":
                _ensure_venda_pago_integral(c4, int(vid))
            elif st == "REALIZADO_PENDENTE_PGTO":
                _ensure_venda_pago_parcial(c4, int(vid))

    conn4.commit()
    conn4.close()

    for aid, st in zip(ag_ids, status_targets):
        if st in ("PRE_AGENDADO", "CANCELADO", "AGENDADO"):
            continue
        if st == "CONFIRMADO":
            alterar_status(aid, "CONFIRMADO")
        elif st == "REALIZADO_PENDENTE_PGTO":
            alterar_status(aid, "CONFIRMADO")
            alterar_status(aid, "CONCLUIDO")
        elif st == "CONCLUIDO":
            alterar_status(aid, "CONCLUIDO")

    # Marcar alguns repasses como pagos
    conn5 = sqlite3.connect(str(db_path))
    c5 = conn5.cursor()
    c5.execute("SELECT id FROM repasse_linhas ORDER BY RANDOM() LIMIT 120")
    for (rid,) in c5.fetchall():
        c5.execute(
            """
            UPDATE repasse_linhas SET status_repasse='REPASSE_PAGO', pago_em=date('now')
            WHERE id=?
            """,
            (rid,),
        )
    conn5.commit()
    conn5.close()

    if not args.no_etl:
        try:
            from scripts.etl_analytics import run_etl

            c = sqlite3.connect(str(db_path))
            run_etl(c)
            c.commit()
            c.close()
        except Exception as e:
            print(f"Aviso: ETL não executado ({e}).", file=sys.stderr)

    # Resumo
    cx = sqlite3.connect(str(db_path)).cursor()
    def cnt(t):
        cx.execute(f"SELECT COUNT(*) FROM {t}")
        return cx.fetchone()[0]

    print("Seed concluído:", db_path)
    print(f"  clientes={cnt('clientes')} colaboradores={cnt('colaboradores')} servicos={cnt('servicos')}")
    print(f"  vendas={cnt('vendas')} agendamentos={cnt('agendamentos')} repasse_linhas={cnt('repasse_linhas')}")
    cx.execute("SELECT status, COUNT(*) FROM agendamentos GROUP BY status")
    print("  agendamentos por status:", dict(cx.fetchall()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

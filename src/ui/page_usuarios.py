"""
Gestão de utilizadores da aplicação — apenas perfil ``admin``.

Constituição Visual BeaBá Sereno (Horizonte + ilhas).

"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.modules.usuarios_db import (
    alternar_status_ativo,
    atualizar_perfil,
    criar_usuario,
    listar_usuarios,
    senha_padrao_inicial,
)
from src.ui.constituicao_visual_shell import (
    CV_CREME,
    CV_SALVIA,
    CV_SOMBRA_COMPOSTA,
    CV_TITULO,
    inject_constituicao_usuarios_page,
)


def _badge_estado_html(ativo: int) -> str:
    """Badges conforme Template Master §5 (sucesso vs terracotta alerta)."""
    if int(ativo):
        return (
            '<span style="display:inline-block;padding:4px 10px;border-radius:12px;font-size:12px;'
            'font-weight:600;background:rgba(232,240,234,0.95);color:#76947D;">Activo</span>'
        )
    return (
        '<span style="display:inline-block;padding:4px 10px;border-radius:12px;font-size:12px;'
        'font-weight:600;background:#FFF4E5;color:#D4A373;">Inactivo</span>'
    )


def _estado_etiqueta_tabela(ativo: int) -> str:
    return "✓ Activo" if int(ativo) else "○ Inactivo"


def render_page_usuarios() -> None:
    inject_constituicao_usuarios_page()
    actor = str(st.session_state.get("auth_user_email") or "").strip()

    st.markdown(
        f'<div style="background:linear-gradient(145deg,#ffffff 0%,{CV_CREME} 120%);'
        f"border-radius:20px;padding:clamp(22px,2.5vw,30px);"
        f"box-shadow:{CV_SOMBRA_COMPOSTA};"
        'border:1px solid rgba(118,148,125,0.18);margin-bottom:20px;">'
        f'<div style="font-size:0.72rem;letter-spacing:0.22em;text-transform:uppercase;'
        f'color:{CV_SALVIA};font-weight:600;margin-bottom:0.35rem;">Administração</div>'
        f'<h1 style="font-family:var(--cv-serif,Georgia,serif);color:{CV_TITULO};margin:0 0 0.5rem;'
        'font-size:1.65rem;font-weight:600;line-height:1.25;">Gestão de utilizadores</h1>'
        '<p style="color:rgba(45,51,47,0.72);margin:0;">'
        "Criação de contas da equipa, perfis de acesso e estado das contas."
        "</p></div>",
        unsafe_allow_html=True,
    )
    rows = listar_usuarios()

    exp_lista = st.expander("1. Lista de utilizadores", expanded=True)
    with exp_lista:
        if not rows:
            st.info("Sem utilizadores registados.")
        else:
            st.markdown("**Legendas:**")
            lc1, lc2 = st.columns(2)
            with lc1:
                st.markdown(_badge_estado_html(1), unsafe_allow_html=True)
            with lc2:
                st.markdown(_badge_estado_html(0), unsafe_allow_html=True)

            vis = []
            for r in rows:
                pend_txt = (
                    "Troca de senha pendente"
                    if int(r.get("must_change_password") or 0)
                    else "—"
                )
                vis.append(
                    {
                        "ID": r["id"],
                        "Nome": r["nome"],
                        "E-mail": r["email"],
                        "Perfil": r["perfil"],
                        "Estado": _estado_etiqueta_tabela(int(r["ativo"])),
                        "Senha inicial / reset": pend_txt,
                        "Cadastro": r.get("data_cadastro") or "—",
                    }
                )
            df = pd.DataFrame(vis)
            try:
                st.dataframe(df, hide_index=True, width="stretch", disabled=True)
            except TypeError:
                st.dataframe(df, hide_index=True, width="stretch")

    exp_novo = st.expander("2. Criar novo utilizador", expanded=False)
    with exp_novo:
        pwd_std = senha_padrao_inicial()
        st.markdown(
            f"Todos os novos registos iniciam com a senha **`{pwd_std}`** e **deverão alterá‑la "
            "(ou usar **«Esqueci minha senha»** no primeiro login, após MFA)."
        )
        with st.form("bea_usuario_criar_form"):
            n_nome = st.text_input("Nome completo")
            n_email = st.text_input("E-mail")
            n_perfil = st.selectbox(
                "Perfil",
                options=["usuario", "admin"],
                index=0,
                help="'usuario' só acede ao Início, Vendas e Clientes / Agendamentos.",
            )
            sub_cria = st.form_submit_button("Criar utilizador", type="primary", width="stretch")
        if sub_cria:
            try:
                new_id = criar_usuario(n_nome.strip(), n_email.strip(), str(n_perfil), actor)
                st.success(
                    f"Utilizador criado (**id {new_id}**). Informe ao colega a senha inicial **`{pwd_std}`** "
                    "— no primeiro login o sistema pedirá uma nova senha."
                )
                st.rerun()
            except ValueError as ve:
                st.error(str(ve))

    opc_ids = [(r["id"], f"{r['nome']} ({r['email']}) — {_estado_etiqueta_tabela(int(r['ativo']))}") for r in rows]
    ids_only = [o[0] for o in opc_ids]
    lbl_map = dict(opc_ids) if opc_ids else {}

    exp_acoes = st.expander("3. Ações rápidas — perfil ou estado da conta", expanded=False)
    with exp_acoes:
        if not ids_only:
            st.caption("Crie primeiro um utilizador na secção acima.")
        else:
            pick = st.selectbox(
                "Selecione o utilizador",
                format_func=lambda x: lbl_map[x],
                options=ids_only,
                key="bea_usuario_pick_acoes",
            )
            nc1, nc2 = st.columns(2)
            with nc1:
                novo_perfil = st.selectbox(
                    "Novo perfil",
                    ["usuario", "admin"],
                    key="bea_usuario_novo_perfil",
                )
                if st.button("Guardar novo perfil", key="bea_usuario_btn_perfil", width="stretch"):
                    ok = atualizar_perfil(int(pick), str(novo_perfil), actor)
                    if ok:
                        st.success("Perfil actualizado.")
                        st.rerun()
                    else:
                        st.error(
                            "Não foi possível alterar o perfil (último administrador ou "
                            "tentativa de retirar o seu próprio acesso)."
                        )
            with nc2:
                atual = next((r for r in rows if int(r["id"]) == int(pick)), None)
                destino = (
                    "Desactivar conta"
                    if atual and int(atual["ativo"])
                    else "Reactivar conta"
                )
                if st.button(destino, key="bea_usuario_btn_toggle_active", width="stretch"):
                    alvo = 0 if (atual and int(atual["ativo"])) else 1
                    ok = alternar_status_ativo(int(pick), alvo, actor)
                    if ok:
                        st.success("Estado actualizado.")
                        st.rerun()
                    else:
                        st.error(
                            "Operação não permitida (único administrador activo ou não pode "
                            "desactivar o seu próprio acesso)."
                        )

"""
Autenticação — login, MFA por e-mail (Constituição Visual BeaBá Sereno).
"""

from __future__ import annotations

import streamlit as st

from src.modules.auth_db import (
    consume_mfa_token,
    discard_pending_mfa_tokens,
    get_usuario_por_id,
    issue_mfa_token,
    try_login_credentials,
    update_password_clear_must_change,
)
from src.modules.auth_utils import generate_mfa_code
from src.modules.email_utils import send_mfa_email
from src.ui.constituicao_visual_shell import CV_CREME, CV_SALVIA, CV_SOMBRA_COMPOSTA, CV_TITULO


def _inject_auth_shell_css() -> None:
    st.markdown(
        f"""
<style>
  .bea-auth-page {{
    font-family: var(--cv-sans, Montserrat, system-ui, sans-serif);
    min-height: 75vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.25rem 0.75rem;
  }}
  .bea-auth-island {{
    width: min(440px, 100%);
    background: linear-gradient(145deg, #ffffff 0%, {CV_CREME} 120%);
    border-radius: var(--cv-radius-isla, 20px);
    padding: 2rem 2.25rem 2.25rem;
    box-shadow: {CV_SOMBRA_COMPOSTA};
    border: 1px solid rgba(118, 148, 125, 0.18);
  }}
  .bea-auth-kicker {{
    font-size: 0.72rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: {CV_SALVIA};
    font-weight: 600;
    margin-bottom: 0.35rem;
  }}
  .bea-auth-title {{
    font-family: var(--cv-serif, Lora, Georgia, serif);
    color: {CV_TITULO};
    font-size: 1.65rem;
    font-weight: 600;
    line-height: 1.25;
    margin: 0 0 0.75rem;
  }}
  .bea-auth-sub {{
    color: rgba(45, 51, 47, 0.72);
    font-size: 0.95rem;
    margin-bottom: 1.35rem;
  }}
</style>
        """,
        unsafe_allow_html=True,
    )


def clear_session_full() -> None:
    """Remove todo o estado de sessão (logout) e força rerun."""
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


def _reset_mfa_state() -> None:
    st.session_state.pop("pending_mfa_user_id", None)
    st.session_state.pop("pending_mfa_email", None)
    st.session_state.pop("aguardando_mfa", None)


def render_login_screen() -> None:
    """Campos e-mail/senha; MFA e envio de e-mail após validação."""
    _inject_auth_shell_css()

    outer_l, outer_c, outer_r = st.columns([1, 2.2, 1])
    with outer_c:
        st.markdown(
            f'<div class="bea-auth-island">'
            f'<div class="bea-auth-kicker">BeaBa Sereno</div>'
            f'<h1 class="bea-auth-title">Entrar na gestão</h1>'
            '<p class="bea-auth-sub">Credenciais da sua equipa. Segue-se uma verificação '
            "do código enviado para o seu e-mail.</p></div>",
            unsafe_allow_html=True,
        )
        with st.form("bea_login_form"):
            email = st.text_input("E-mail")
            pwd = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", type="primary", width="stretch")
        if submitted:
            if not (email.strip() and pwd.strip()):
                st.warning("Informe e-mail e senha.")
                return
            user, msg = try_login_credentials(email.strip(), pwd)
            if not user:
                if msg:
                    st.error(msg)
                else:
                    st.error("Não foi possível validar o acesso.")
                return
            code = generate_mfa_code()
            dberr = issue_mfa_token(int(user["id"]), code)
            if dberr:
                st.error(dberr)
                return
            try:
                send_mfa_email(str(user["email"]), code)
            except Exception as err:
                discard_pending_mfa_tokens(int(user["id"]))
                st.error(
                    "Não foi possível enviar o e-mail com o código. No `.env` (raiz do projecto): "
                    "SMTP_USER ou EMAIL_USERNAME + SMTP_PASSWORD ou EMAIL_PASSWORD (Gmail = palavra-passe "
                    "de *aplicação*, 16 caracteres sem espaços); confirme pasta de trabalho antes de iniciar Streamlit. "
                    f"Pormenores: {err!s}"
                )
                return
            st.session_state.pending_mfa_user_id = int(user["id"])
            st.session_state.pending_mfa_email = str(user["email"])
            st.session_state.aguardando_mfa = True
            st.success("Enviamos um código de verificação para o seu e-mail.")
            st.rerun()


def render_mfa_screen() -> None:
    """Validação dos 6 dígitos e conclusão de sessão."""
    uid = int(st.session_state.pending_mfa_user_id)
    hint = str(st.session_state.get("pending_mfa_email") or "").strip()

    _inject_auth_shell_css()
    outer_l, outer_c, outer_r = st.columns([1, 2.2, 1])
    with outer_c:
        frag = (
            f'<div class="bea-auth-island">'
            f'<div class="bea-auth-kicker">Verificação</div>'
            f'<h1 class="bea-auth-title">Código de acesso</h1>'
            f'<p class="bea-auth-sub">'
        )
        frag += (
            f'Introduza os 6 dígitos enviados para <strong>{hint}</strong>.'
            if hint
            else "Introduza os 6 dígitos enviados por e-mail."
        )
        frag += "</p></div>"
        st.markdown(frag, unsafe_allow_html=True)

        code_in = st.text_input(
            "Código de 6 dígitos",
            max_chars=6,
            key="bea_mfa_code_input",
        )

        ca, cb = st.columns(2)
        if ca.button("Validar código", type="primary", width="stretch", key="bea_mfa_submit"):
            if not (code_in and code_in.strip().isdigit() and len(code_in.strip()) == 6):
                st.error("Informe um código numérico de 6 dígitos.")
            elif not consume_mfa_token(uid, code_in.strip()):
                st.error("Código incorreto ou expirado.")
            else:
                row = get_usuario_por_id(uid)
                if not row:
                    st.error("Não foi possível concluir a sessão.")
                else:
                    _reset_mfa_state()
                    st.session_state.authenticated = True
                    st.session_state.auth_user_id = row["id"]
                    st.session_state.auth_user_email = row["email"]
                    st.session_state.auth_user_nome = row["nome"]
                    st.session_state.auth_perfil = row["perfil"]
                    st.session_state.auth_must_change_password = bool(
                        row.get("must_change_password", False)
                    )
                    st.rerun()

        if cb.button("Voltar ao início de sessão", width="stretch", key="bea_mfa_cancel"):
            discard_pending_mfa_tokens(uid)
            _reset_mfa_state()
            st.rerun()


def render_force_password_change() -> None:
    """Obrigatório após MFA quando ``must_change_password`` está activo (primeiro acesso ou conta nova)."""
    _inject_auth_shell_css()
    uid = int(st.session_state.get("auth_user_id") or 0)
    if not uid:
        clear_session_full()
        return

    outer_l, outer_c, outer_r = st.columns([1, 2.2, 1])
    with outer_c:
        st.markdown(
            f'<div class="bea-auth-island">'
            f'<div class="bea-auth-kicker">Segurança</div>'
            f'<h1 class="bea-auth-title">Definir nova senha</h1>'
            "<p class=\"bea-auth-sub\">É obrigatório alterar a senha antes de continuar. "
            "Utilize uma palavra-passe forte (mínimo 8 caracteres), diferente da actual.</p></div>",
            unsafe_allow_html=True,
        )
        with st.form("bea_force_password_form"):
            cur = st.text_input("Senha actual", type="password")
            n1 = st.text_input("Nova senha", type="password")
            n2 = st.text_input("Confirmar nova senha", type="password")
            submitted = st.form_submit_button("Guardar e continuar", type="primary", width="stretch")
        if submitted:
            if not (cur.strip() and n1.strip() and n2.strip()):
                st.warning("Preencha todos os campos.")
            elif n1.strip() != n2.strip():
                st.error("A confirmação da nova senha não coincide.")
            else:
                err = update_password_clear_must_change(
                    uid, n1.strip(), current_password=cur.strip()
                )
                if err:
                    st.error(err)
                else:
                    st.session_state.auth_must_change_password = False
                    st.success("Senha actualizada. A redireccionar…")
                    st.rerun()

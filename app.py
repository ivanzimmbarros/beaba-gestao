import streamlit as st
from src.database.connection import init_db
from src.models.cliente import cadastrar_cliente

init_db()
st.set_page_config(page_title="BeaBa Gestão", layout="centered")
st.markdown("<h1 style='color: #D4AF37; text-align: center;'>⚜️ BeaBa Gestão</h1>", unsafe_allow_html=True)

with st.form("form_cadastro", clear_on_submit=True):
    nome = st.text_input("Nome Completo")
    whatsapp = st.text_input("WhatsApp (DDD + Número)")
    if st.form_submit_button("CADASTRAR CLIENTE", use_container_width=True):
        sucesso, msg = cadastrar_cliente(nome, whatsapp)
        if sucesso: st.success(msg)
        else: st.error(msg)
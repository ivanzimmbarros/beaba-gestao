import streamlit as st
from src.database.connection import create_tables
from src.modules.cliente import cadastrar_cliente

# Inicializa o banco de dados e tabelas
create_tables()

st.set_page_config(page_title="BeaBa Gestão", page_icon="⚜️")

st.markdown("<h1 style='text-align: center; color: #D4AF37;'>⚜️ BeaBa Gestão</h1>", unsafe_allow_html=True)

with st.container():
    st.markdown("---")
    nome = st.text_input("Nome Completo")
    whatsapp = st.text_input("WhatsApp (DDD + Número)")
    
    if st.button("CADASTRAR CLIENTE", use_container_width=True):
        if nome and whatsapp:
            # Chama o módulo de cliente com tratamento de erro amigável
            resultado = cadastrar_cliente(nome, whatsapp)
            
            if resultado == True:
                st.success(f"✅ {nome} cadastrado com sucesso!")
            else:
                # Exibe a mensagem de erro específica (duplicidade ou formato)
                st.error(f"⚠️ {resultado}")
        else:
            st.warning("Please, preencha todos os campos.")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO DE ACESSO (Mantenha sua lógica de senha) ---
SENHA_CORRETA = "1234"

def validar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.title("🔒 Acesso Restrito")
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar"):
            if senha == SENHA_CORRETA:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
        return False
    return True

st.set_page_config(page_title="Financeiro Cloud", layout="wide")

if validar_login():
    # CONEXÃO COM GOOGLE SHEETS
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Função para ler dados das abas
    def carregar_dados():
        try:
            r = conn.read(worksheet="receitas")
            g = conn.read(worksheet="gastos")
            i = conn.read(worksheet="investimentos")
            return pd.concat([r, g, i], ignore_index=True)
        except:
            return pd.DataFrame(columns=["data", "tipo", "categoria", "valor"])

    df = carregar_dados()

    # --- LÓGICA DE TRATAMENTO DE DADOS (Igual a anterior) ---
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
        df["valor"] = df["valor"].astype(float)
        # ... (restante dos cálculos de mês/ano aqui)

    # --- NOVO REGISTRO (ADAPTADO PARA SHEETS) ---
    st.subheader("➕ Novo Registro")
    # ... (campos do formulário aqui)

    if st.button("Salvar no Cloud"):
        # Criar DataFrame com o novo dado
        novo_dado = pd.DataFrame([[str(dt), tipo, cat, val]], columns=["data","tipo","categoria","valor"])
        
        # Carregar dados existentes da aba específica
        aba = "receitas" if tipo=="Receita" else "gastos" if tipo=="Gasto" else "investimentos"
        df_existente = conn.read(worksheet=aba)
        df_atualizado = pd.concat([df_existente, novo_dado], ignore_index=True)
        
        # Salvar de volta no Google Sheets
        conn.update(worksheet=aba, data=df_atualizado)
        st.success("Dados salvos na nuvem!")
        st.rerun()

    # --- RESTANTE DO DASHBOARD (GRÁFICOS) ---
    # (O código dos gráficos permanece o mesmo, pois o DF é o mesmo)
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

    if st.button("Salvar no Google Sheets", use_container_width=True):
            try:
                # 1. Identifica a aba
                aba = "receitas" if tipo=="Receita" else "gastos" if tipo=="Gasto" else "investimentos"
                
                # 2. Tenta ler os dados atuais. Se der erro, cria um DF vazio com colunas
                try:
                    dados_atuais = conn.read(worksheet=aba, ttl=0)
                except Exception:
                    dados_atuais = pd.DataFrame(columns=["data","tipo","categoria","valor"])
                
                # 3. Prepara a linha para salvar
                novo_reg = pd.DataFrame([[str(dt), tipo, cat, val]], columns=["data","tipo","categoria","valor"])
                
                # 4. Une e atualiza
                df_update = pd.concat([dados_atuais, novo_reg], ignore_index=True)
                conn.update(worksheet=aba, data=df_update)
                
                st.success("Dados sincronizados!")
                st.cache_data.clear() 
                st.rerun()
            except Exception as e:
                st.error(f"Erro detalhado: {e}")

    # --- RESTANTE DO DASHBOARD (GRÁFICOS) ---
    # (O código dos gráficos permanece o mesmo, pois o DF é o mesmo)

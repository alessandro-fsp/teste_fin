import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# =========================
# CONFIGURAÇÃO DE ACESSO
# =========================
def validar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("🔒 Acesso Restrito")
        # Busca a senha do painel Secrets do Streamlit Cloud
        try:
            SENHA_CORRETA = st.secrets["senha_acesso"]
        except:
            st.error("Erro: 'senha_acesso' não configurada nos Secrets!")
            return False

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
    # Conexão com Google Sheets usando a URL dos Secrets
    conn = st.connection("gsheets", type=GSheetsConnection)

    # =========================
    # FUNÇÕES DE DADOS
    # =========================
    def carregar_aba(nome_aba):
        try:
            # ttl=0 garante que ele busque o dado mais fresco ao salvar
            return conn.read(worksheet=nome_aba, ttl="1m")
        except:
            # Se a aba não existir ou estiver vazia, retorna estrutura padrão
            return pd.DataFrame(columns=["data", "tipo", "categoria", "valor"])

    def atualizar_dados():
        df_rec = carregar_aba("receitas")
        df_gas = carregar_aba("gastos")
        df_inv = carregar_aba("investimentos")
        
        combined = pd.concat([df_rec, df_gas, df_inv], ignore_index=True)
        if not combined.empty:
            combined["data"] = pd.to_datetime(combined["data"], errors='coerce')
            combined["valor"] = pd.to_numeric(combined["valor"], errors='coerce').fillna(0)
        return combined

    df = atualizar_dados()

    # Processamento para Gráficos
    meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 
                7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}

    if not df.empty and "data" in df.columns:
        df = df.dropna(subset=["data"])
        df["ano"] = df["data"].dt.year
        df["mes"] = df["data"].dt.month
        df["mes_nome"] = df["mes"].map(meses_pt) + "/" + df["ano"].astype(str)
        df["data_br"] = df["data"].dt.strftime("%d/%m/%Y")
        df = df.reset_index().rename(columns={'index': 'ID'})

    # =========================
    # SIDEBAR
    # =========================
    st.sidebar.title("⚙️ Filtros")
    if st.sidebar.button("Sair / Bloquear"):
        st.session_state["autenticado"] = False
        st.rerun()

    hoje = datetime.today()
    anos_list = ["Todos"] + sorted(df["ano"].unique().tolist()) if not df.empty else ["Todos"]
    ano_sel = st.sidebar.selectbox("Ano", anos_list, index=0)
    mes_sel = st.sidebar.selectbox("Mês", ["Todos"] + list(range(1, 13)), index=hoje.month)

    df_filtrado = df.copy() if not df.empty else pd.DataFrame()
    if not df.empty:
        if ano_sel != "Todos": df_filtrado = df_filtrado[df_filtrado["ano"] == ano_sel]
        if mes_sel != "Todos": df_filtrado = df_filtrado[df_filtrado["mes"] == mes_sel]

    # =========================
    # INTERFACE
    # =========================
    col1, col2 = st.columns([1, 1.6])

    with col1:
        st.subheader("➕ Novo Registro")
        tipo = st.selectbox("Tipo", ["Receita","Gasto","Investimento"])
        cats = {"Receita": ["Salário", "Outros"], 
                "Gasto": ["Supermercado","Lanches","Restaurante","Transporte","Contas","Lazer","Outros"],
                "Investimento": ["Renda Fixa","Ações","FII","Cripto","Outros"]}
        cat = st.selectbox("Categoria", cats[tipo])
        dt = st.date_input("Data", hoje, format="DD/MM/YYYY")
        val = st.number_input("Valor", min_value=0.0, step=10.0)

        if st.button("Salvar no Cloud", use_container_width=True):
            aba_alvo = "receitas" if tipo=="Receita" else "gastos" if tipo=="Gasto" else "investimentos"
            
            # Lê o que já existe na aba específica para não sobrescrever
            df_atual = carregar_aba(aba_alvo)
            novo_reg = pd.DataFrame([[str(dt), tipo, cat, val]], columns=["data","tipo","categoria","valor"])
            
            df_final = pd.concat([df_atual, novo_reg], ignore_index=True)
            
            # Envia para o Google Sheets
            conn.update(worksheet=aba_alvo, data=df_final)
            st.success("Sincronizado!")
            st.cache_data.clear()
            st.rerun()

    with col2:
        st.markdown("### 📋 Movimentações")
        if not df_filtrado.empty:
            st.dataframe(
                df_filtrado[["ID", "data_br", "tipo", "categoria", "valor"]],
                column_config={"valor": st.column_config.NumberColumn("R$", format="%.2f")},
                hide_index=True, use_container_width=True, height=250
            )
            st.caption("Para deletar: Edite diretamente sua planilha Google Sheets.")
        else:
            st.info("Nenhum dado encontrado para os filtros selecionados.")

    # =========================
    # DASHBOARD
    # =========================
    if not df_filtrado.empty:
        st.divider()
        rec = df_filtrado[df_filtrado["tipo"]=="Receita"]["valor"].sum()
        gas = df_filtrado[df_filtrado["tipo"]=="Gasto"]["valor"].sum()
        inv = df_filtrado[df_filtrado["tipo"]=="Investimento"]["valor"].sum()

        c = st.columns(4)
        c[0].metric("Receitas", f"R$ {rec:,.2f}")
        c[1].metric("Gastos", f"R$ {gas:,.2f}")
        c[2].metric("Invests", f"R$ {inv:,.2f}")
        c[3].metric("Sobra Real", f"R$ {rec-gas-inv:,.2f}")

        st.write("")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("### 📊 Entradas vs Saídas")
            df_g = df_filtrado.copy()
            df_g["status"] = df_g["tipo"].apply(lambda x: "Receita" if x=="Receita" else "Saída")
            fig1 = px.bar(df_g, x="mes_nome", y="valor", color="tipo", barmode="group",
                          color_discrete_map={"Receita":"#2ecc71","Gasto":"#e74c3c","Investimento":"#3498db"})
            st.plotly_chart(fig1, use_container_width=True)
        
        with g2:
            st.markdown("### 🥧 Gastos por Categoria")
            fig2 = px.pie(df_filtrado[df_filtrado["tipo"]=="Gasto"], names="categoria", values="valor", hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)

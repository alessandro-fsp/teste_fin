import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO DE ACESSO VIA SECRETS ---
def validar_login():
    # Busca a senha definida no secrets.toml
    SENHA_CORRETA = st.secrets["senha_acesso"]
    
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("🔒 Acesso Restrito")
        senha = st.text_input("Digite a senha para acessar o painel:", type="password")
        if st.button("Entrar"):
            if senha == SENHA_CORRETA:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
        return False
    return True

st.set_page_config(page_title="Controle Financeiro Cloud", layout="wide")

if validar_login():
    # Botão de Logout
    if st.sidebar.button("Sair / Bloquear"):
        st.session_state["autenticado"] = False
        st.rerun()

    # =========================
    # CONEXÃO COM GOOGLE SHEETS
    # =========================
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Função para carregar todas as abas e unir em um DataFrame
    @st.cache_data(ttl=60) # Atualiza o cache a cada 60 segundos
    def carregar_tudo():
        try:
            # Lê cada aba (as abas devem ter esses nomes exatos no Sheets)
            df_rec = conn.read(worksheet="receitas")
            df_gas = conn.read(worksheet="gastos")
            df_inv = conn.read(worksheet="investimentos")
            
            combined = pd.concat([df_rec, df_gas, df_inv], ignore_index=True)
            
            if not combined.empty:
                combined["data"] = pd.to_datetime(combined["data"])
                combined["valor"] = pd.to_numeric(combined["valor"])
            return combined
        except Exception as e:
            return pd.DataFrame(columns=["data","tipo","categoria","valor"])

    df = carregar_tudo()

    # --- PROCESSAMENTO ---
    meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 
                7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}

    if not df.empty:
        df["ano"] = df["data"].dt.year
        df["mes"] = df["data"].dt.month
        df["mes_nome"] = df["mes"].map(meses_pt) + "/" + df["ano"].astype(str)
        df["data_br"] = df["data"].dt.strftime("%d/%m/%Y")
        df["valor_num"] = df["valor"].astype(float)
        df = df.reset_index().rename(columns={'index': 'ID'})

    # =========================
    # SIDEBAR / FILTROS
    # =========================
    hoje = datetime.today()
    st.sidebar.title("⚙️ Filtros")
    anos_list = ["Todos"] + sorted(df["ano"].unique().tolist()) if not df.empty else ["Todos"]
    
    try: idx_ano = anos_list.index(hoje.year)
    except: idx_ano = 0

    ano_sel = st.sidebar.selectbox("Ano", anos_list, index=idx_ano)
    mes_sel = st.sidebar.selectbox("Mês", ["Todos"] + list(range(1, 13)), index=hoje.month)

    df_filtrado = df.copy() if not df.empty else pd.DataFrame()
    if not df.empty:
        if ano_sel != "Todos": df_filtrado = df_filtrado[df_filtrado["ano"] == ano_sel]
        if mes_sel != "Todos": df_filtrado = df_filtrado[df_filtrado["mes"] == mes_sel]

    # =========================
    # INTERFACE PRINCIPAL
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

        if st.button("Salvar no Google Sheets", use_container_width=True):
            # 1. Prepara a linha para salvar
            novo_reg = pd.DataFrame([[str(dt), tipo, cat, val]], columns=["data","tipo","categoria","valor"])
            
            # 2. Identifica a aba e lê o que já existe nela
            aba = "receitas" if tipo=="Receita" else "gastos" if tipo=="Gasto" else "investimentos"
            dados_atuais = conn.read(worksheet=aba)
            
            # 3. Une e atualiza a planilha
            df_update = pd.concat([dados_atuais, novo_reg], ignore_index=True)
            conn.update(worksheet=aba, data=df_update)
            
            st.success("Dados sincronizados com a nuvem!")
            st.cache_data.clear() # Limpa o cache para mostrar o dado novo
            st.rerun()

    with col2:
        st.markdown("### 📋 Movimentações (Cloud)")
        if not df_filtrado.empty:
            def colorir(row):
                colors = {"Receita": "#2ecc71", "Gasto": "#e74c3c", "Investimento": "#3498db"}
                return [f'color: {colors.get(row["tipo"], "white")}'] * len(row)

            st.dataframe(
                df_filtrado[["ID", "data_br", "tipo", "categoria", "valor_num"]].style.apply(colorir, axis=1),
                column_config={"valor_num": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
                hide_index=True, use_container_width=True, height=300
            )
            st.info("Para deletar registros, edite diretamente sua planilha no Google Sheets.")
        else:
            st.info("Aguardando dados ou planilha vazia.")

    # =========================
    # DASHBOARD
    # =========================
    if not df_filtrado.empty:
        st.divider()
        rec = df_filtrado[df_filtrado["tipo"]=="Receita"]["valor_num"].sum()
        gas = df_filtrado[df_filtrado["tipo"]=="Gasto"]["valor_num"].sum()
        inv = df_filtrado[df_filtrado["tipo"]=="Investimento"]["valor_num"].sum()

        # Cards de Resumo
        cols_cards = st.columns(4)
        cards = [("Receitas", rec, "#2ecc71"), ("Gastos", gas, "#e74c3c"), 
                 ("Invests", inv, "#3498db"), ("Sobra", rec-gas-inv, "white")]
        
        for i, (label, value, color) in enumerate(cards):
            with cols_cards[i]:
                st.markdown(f"""
                    <div style="background:#1e1e1e; padding:15px; border-radius:10px; border-left: 5px solid {color};">
                        <small style="color:gray;">{label}</small><br>
                        <b style="font-size:18px; color:white;">R$ {value:,.2f}</b>
                    </div>
                """, unsafe_allow_html=True)

        # Gráficos
        st.write("") # Espaçamento
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📊 Receita vs Saídas")
            df_g = df_filtrado.copy()
            df_g["gp"] = df_g["tipo"].apply(lambda x: "Receita" if x=="Receita" else "Saídas")
            fig1 = px.bar(df_g.groupby(["mes_nome", "gp", "tipo"])["valor_num"].sum().reset_index(), 
                          x="mes_nome", y="valor_num", color="tipo", barmode="relative",
                          color_discrete_map={"Receita":"#2ecc71","Gasto":"#e74c3c","Investimento":"#3498db"})
            fig1.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None, margin=dict(t=0,b=0))
            st.plotly_chart(fig1, use_container_width=True)

        with c2:
            st.markdown("### 🥧 Gastos")
            g_df = df_filtrado[df_filtrado["tipo"]=="Gasto"]
            if not g_df.empty:
                fig2 = px.pie(g_df.groupby("categoria")["valor_num"].sum().reset_index(), 
                              names="categoria", values="valor_num", hole=0.5)
                fig2.update_layout(margin=dict(t=0,b=0))
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown("### 📈 Evolução Saldo")
        d_ev = df_filtrado.sort_values("data").copy()
        d_ev["mov"] = d_ev.apply(lambda x: x["valor_num"] if x["tipo"]=="Receita" else -x["valor_num"], axis=1)
        d_ev["acumulado"] = d_ev["mov"].cumsum()
        fig5 = px.line(d_ev, x="data", y="acumulado")
        fig5.update_traces(line_color="#2ecc71")
        fig5.update_layout(xaxis_title=None, yaxis_title=None, height=300)
        st.plotly_chart(fig5, use_container_width=True)

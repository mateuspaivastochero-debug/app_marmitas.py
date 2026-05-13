import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# CONFIGURAÇÕES
st.set_page_config(page_title="Gestão de Marmitas", layout="wide")

# URL da sua planilha (Substitua pelo seu link real abaixo)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1rjxVMvNuok2KN2aO2hJGtuCtb2R0YCPwdx9TiS74e3o/edit"

USUARIOS = {"Lidiane": "1234", "Mateus": "4321"}

def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if not st.session_state.autenticado:
        st.title("🔐 Acesso ao Sistema")
        user_select = st.selectbox("Usuário:", list(USUARIOS.keys()))
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar"):
            if USUARIOS.get(user_select) == senha:
                st.session_state.autenticado = True
                st.session_state.usuario_atual = user_select
                st.rerun()
            else:
                st.error("Senha incorreta!")
        return False
    return True

if login():
    # Conexão com Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def ler_dados():
        df_c = conn.read(spreadsheet=URL_PLANILHA, worksheet="cadastro", ttl=0)
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="movimentacoes", ttl=0)
        return df_c, df_m

    df_cadastro, df_movimentacoes = ler_dados()

    st.sidebar.title(f"Olá, {st.session_state.usuario_atual}!")
    opcao = st.sidebar.radio("Navegação:", ["Nova Venda/Produção", "Painel de Estoque", "Balanço Financeiro", "Cadastro de Produtos", "Sair"])

    if opcao == "Sair":
        st.session_state.autenticado = False
        st.rerun()

    # --- TELA: NOVA VENDA ---
    if opcao == "Nova Venda/Produção":
        st.header("🛒 Registrar Operação")
        with st.form("venda_form", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Saída (Venda)", "Entrada (Produção)"])
            produto = st.selectbox("Produto", df_cadastro['Código'] + " - " + df_cadastro['Sabor'])
            qtd = st.number_input("Quantidade", min_value=1)
            obs = st.text_input("Observação")
            
            if st.form_submit_button("Salvar na Planilha"):
                cod = produto.split(" - ")[0]
                row = df_cadastro[df_cadastro['Código'] == cod].iloc[0]
                preco = row['Preço Venda'] if "Saída" in tipo else row['Valor Pago']
                total = float(preco) * qtd
                
                novo_registro = pd.DataFrame([{
                    "Data": date.today().strftime("%d/%m/%Y"),
                    "Tipo": "Saída" if "Saída" in tipo else "Entrada",
                    "Código": cod,
                    "Quantidade": qtd,
                    "Valor Total": total,
                    "Cliente/Obs": f"Por: {st.session_state.usuario_atual} | {obs}"
                }])
                
                df_atualizado = pd.concat([df_movimentacoes, novo_registro], ignore_index=True)
                conn.update(spreadsheet=URL_PLANILHA, worksheet="movimentacoes", data=df_atualizado)
                st.success("Dados salvos diretamente no Google Sheets!")
                st.rerun()

    # --- TELA: BALANÇO ---
    elif opcao == "Balanço Financeiro":
        st.header("📊 Balanço Real")
        investido = df_movimentacoes[df_movimentacoes['Tipo'] == 'Entrada']['Valor Total'].sum()
        vendas = df_movimentacoes[df_movimentacoes['Tipo'] == 'Saída']['Valor Total'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Investimento Total", f"R$ {investido:.2f}")
        c2.metric("Vendas Totais", f"R$ {vendas:.2f}")
        c3.metric("Faturamento (Resultado)", f"R$ {vendas - investido:.2f}")
        
        st.dataframe(df_movimentacoes, use_container_width=True)

    # ... (As outras telas seguem a mesma lógica de conn.update)

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

st.set_page_config(page_title="Gestão de Marmitas", layout="wide")

USUARIOS = {"Lidiane": "1234", "Mateus": "4321"}

def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if not st.session_state.autenticado:
        st.title("🔐 Acesso ao Sistema")
        user = st.selectbox("Usuário:", list(USUARIOS.keys()))
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar"):
            if USUARIOS.get(user) == senha:
                st.session_state.autenticado = True
                st.session_state.usuario_atual = user
                st.rerun()
            else:
                st.error("Senha incorreta!")
        return False
    return True

if login():
    # Conexão automática usando os Secrets que configuramos
    conn = st.connection("gsheets", type=GSheetsConnection)

    df_cadastro = conn.read(worksheet="cadastro", ttl=0)
    df_movimentacoes = conn.read(worksheet="movimentacoes", ttl=0)

    st.sidebar.title(f"Olá, {st.session_state.usuario_atual}!")
    opcao = st.sidebar.radio("Menu:", ["Nova Venda/Produção", "Painel de Estoque", "Balanço Financeiro", "Sair"])

    if opcao == "Sair":
        st.session_state.autenticado = False
        st.rerun()

    if opcao == "Nova Venda/Produção":
        st.header("🛒 Registrar Operação")
        with st.form("registro_form", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Saída (Venda)", "Entrada (Produção)"])
            # Garante que os dados do cadastro existem
            opcoes = df_cadastro['Código'].astype(str) + " - " + df_cadastro['Sabor'].astype(str)
            produto_sel = st.selectbox("Produto", opcoes)
            qtd = st.number_input("Quantidade", min_value=1)
            obs = st.text_input("Observação")
            
            if st.form_submit_button("Gravar na Planilha"):
                cod = produto_sel.split(" - ")[0]
                row_p = df_cadastro[df_cadastro['Código'].astype(str) == cod].iloc[0]
                preco = row_p['Preço Venda'] if "Saída" in tipo else row_p['Valor Pago']
                
                nova_linha = pd.DataFrame([{
                    "Data": date.today().strftime("%d/%m/%Y"),
                    "Tipo": tipo,
                    "Código": cod,
                    "Quantidade": qtd,
                    "Valor Total": float(preco) * qtd,
                    "Cliente/Obs": f"Por: {st.session_state.usuario_atual} | {obs}"
                }])
                
                # Salva direto no Google Sheets!
                df_final = pd.concat([df_movimentacoes, nova_linha], ignore_index=True)
                conn.update(worksheet="movimentacoes", data=df_final)
                st.success("✅ Gravado com sucesso!")
                st.rerun()

    elif opcao == "Balanço Financeiro":
        st.header("📊 Balanço")
        investido = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Entrada', na=False)]['Valor Total'].sum()
        vendas = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Saída', na=False)]['Valor Total'].sum()
        st.columns(3)[0].metric("Investimento", f"R$ {investido:.2f}")
        st.columns(3)[1].metric("Vendas", f"R$ {vendas:.2f}")
        st.columns(3)[2].metric("Resultado", f"R$ {vendas - investido:.2f}")
        st.dataframe(df_movimentacoes, use_container_width=True)

    elif opcao == "Painel de Estoque":
        st.header("📦 Estoque")
        ent = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Entrada', na=False)].groupby('Código')['Quantidade'].sum()
        sai = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Saída', na=False)].groupby('Código')['Quantidade'].sum()
        # Cálculo simples de estoque
        st.write("Consulte o estoque total na planilha ou adicione a lógica de merge aqui.")

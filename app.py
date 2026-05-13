import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão de Marmitas", layout="wide")

# URL da sua planilha (Versão limpa)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1rjxVMvNuok2KN2aO2hJGtuCtb2R0YCPwdx9TiS74e3o/edit"

# Usuários e Senhas
USUARIOS = {
    "Lidiane": "1234",
    "Mateus": "4321"
}

# --- FUNÇÃO DE LOGIN ---
def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None

    if not st.session_state.autenticado:
        st.title("🔐 Acesso ao Sistema")
        user_select = st.selectbox("Selecione o utilizador:", list(USUARIOS.keys()))
        senha = st.text_input("Palavra-passe:", type="password")
        
        if st.button("Entrar"):
            if USUARIOS.get(user_select) == senha:
                st.session_state.autenticado = True
                st.session_state.usuario_atual = user_select
                st.rerun()
            else:
                st.error("Palavra-passe incorreta!")
        return False
    return True

# --- EXECUÇÃO PRINCIPAL ---
if login():
    # Conexão com Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Função para ler dados (ttl=0 garante que os dados não fiquem em cache antigo)
    def buscar_dados():
        df_c = conn.read(spreadsheet=URL_PLANILHA, worksheet="cadastro", ttl=0)
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="movimentacoes", ttl=0)
        return df_c, df_m

    df_cadastro, df_movimentacoes = buscar_dados()

    st.sidebar.title(f"Olá, {st.session_state.usuario_atual}!")
    opcao = st.sidebar.radio("Menu:", ["Nova Venda/Produção", "Painel de Estoque", "Balanço Financeiro", "Cadastro de Produtos", "Sair"])

    if opcao == "Sair":
        st.session_state.autenticado = False
        st.rerun()

    # --- TELA: REGISTRO DE OPERAÇÃO ---
    if opcao == "Nova Venda/Produção":
        st.header("🛒 Registrar Operação")
        if df_cadastro.empty:
            st.warning("Cadastre os produtos primeiro na planilha.")
        else:
            with st.form("form_venda", clear_on_submit=True):
                col1, col2 = st.columns(2)
                tipo = col1.selectbox("Tipo", ["Saída (Venda)", "Entrada (Produção)"])
                
                # Lista de produtos dinâmica
                opcoes = df_cadastro['Código'].astype(str) + " - " + df_cadastro['Sabor'].astype(str)
                produto_sel = col1.selectbox("Produto", opcoes)
                
                qtd = col2.number_input("Quantidade", min_value=1, step=1)
                data_op = col2.date_input("Data", date.today())
                obs = st.text_input("Observação/Cliente")
                
                if st.form_submit_button("Confirmar e Gravar na Planilha"):
                    # Cálculos
                    cod = str(produto_sel).split(" - ")[0]
                    dados_p = df_cadastro[df_cadastro['Código'].astype(str) == cod].iloc[0]
                    preco = dados_p['Preço Venda'] if "Saída" in tipo else dados_p['Valor Pago']
                    total = float(preco) * qtd
                    
                    # Criação da nova linha
                    nova_linha = pd.DataFrame([{
                        "Data": data_op.strftime("%d/%m/%Y"),
                        "Tipo": tipo,
                        "Código": cod,
                        "Quantidade": qtd,
                        "Valor Total": total,
                        "Cliente/Obs": f"Por: {st.session_state.usuario_atual} | {obs}"
                    }])
                    
                    # Atualização automática na planilha
                    df_atualizado = pd.concat([df_movimentacoes, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="movimentacoes", data=df_atualizado)
                    
                    st.success(f"✅ Registado com sucesso por {st.session_state.usuario_atual}!")
                    st.rerun()

    # --- TELA: BALANÇO FINANCEIRO ---
    elif opcao == "Balanço Financeiro":
        st.header("📊 Balanço Financeiro")
        if not df_movimentacoes.empty:
            # Cálculos de faturamento
            investido = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Entrada', na=False)]['Valor Total'].sum()
            vendas = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Saída', na=False)]['Valor Total'].sum()
            lucro = vendas - investido

            c1, c2, c3 = st.columns(3)
            c1.metric("Investimento (Entradas)", f"R$ {investido:.2f}")
            c2.metric("Vendas (Saídas)", f"R$ {vendas:.2f}")
            c3.metric("Resultado Final", f"R$ {lucro:.2f}", delta=f"{lucro:.2f}")

            st.divider()
            st.subheader("Histórico Completo")
            st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

    # --- TELA: ESTOQUE ---
    elif opcao == "Painel de Estoque":
        st.header("📦 Inventário")
        if not df_movimentacoes.empty:
            ent = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Entrada', na=False)].groupby('Código')['Quantidade'].sum().reset_index(name='E')
            sai = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Saída', na=False)].groupby('Código')['Quantidade'].sum().reset_index(name='S')
            stk = pd.merge(df_cadastro[['Código', 'Sabor']], ent, on='Código', how='left').fillna(0)
            stk = pd.merge(stk, sai, on='Código', how='left').fillna(0)
            stk['Stock'] = stk['E'] - stk['S']
            st.dataframe(stk[['Código', 'Sabor', 'Stock']], use_container_width=True, hide_index=True)

    # --- TELA: PRODUTOS ---
    elif opcao == "Cadastro de Produtos":
        st.header("📝 Produtos Disponíveis")
        st.dataframe(df_cadastro, use_container_width=True, hide_index=True)
        st.info("Para alterar preços ou sabores, edite a aba 'cadastro' na sua Planilha Google.")

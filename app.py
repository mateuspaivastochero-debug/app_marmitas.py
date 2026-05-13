import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Gestão de Marmitas", layout="wide")

ID_PLANILHA = "1rjxVMvNuok2KN2aO2hJGtuCtb2R0YCPwdx9TiS74e3o"
URL_CADASTRO = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid=485394711"
URL_MOVIMENTACOES = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid=0"

USUARIOS = {"Lidiane": "1234", "Mateus": "4321"}

# --- FUNÇÃO DE LEITURA (Via Pandas - Rápida) ---
def ler_dados():
    # sep=None com engine='python' detecta automaticamente se é vírgula ou ponto e vírgula
    df_c = pd.read_csv(URL_CADASTRO, sep=None, engine='python', encoding='utf-8')
    df_m = pd.read_csv(URL_MOVIMENTACOES, sep=None, engine='python', encoding='utf-8')
    
    # Limpa nomes de colunas
    df_c.columns = [str(c).strip().replace('ï»¿', '').replace('\ufeff', '') for c in df_c.columns]
    df_m.columns = [str(c).strip().replace('ï»¿', '').replace('\ufeff', '') for c in df_m.columns]
    
    return df_c, df_m

# --- LOGIN ---
def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if not st.session_state.autenticado:
        st.title("🔐 Acesso ao Sistema")
        user_select = st.selectbox("Selecione seu usuário:", list(USUARIOS.keys()))
        senha = st.text_input("Digite sua senha:", type="password")
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
    df_cadastro, df_movimentacoes = ler_dados()
    
    st.sidebar.title(f"Olá, {st.session_state.usuario_atual}!")
    opcao = st.sidebar.radio("Navegação:", ["Nova Venda/Produção", "Painel de Estoque", "Balanço Financeiro", "Cadastro de Produtos", "Sair"])

    if opcao == "Sair":
        st.session_state.autenticado = False
        st.rerun()

    # --- TELA: NOVA VENDA ---
    if opcao == "Nova Venda/Produção":
        st.header("🛒 Registrar Operação")
        if df_cadastro.empty:
            st.warning("Cadastre os produtos primeiro na planilha.")
        else:
            with st.form("form_operacao", clear_on_submit=True):
                col1, col2 = st.columns(2)
                tipo = col1.selectbox("Tipo", ["Saída (Venda)", "Entrada (Produção)"])
                
                # Monta lista de produtos para seleção
                lista_p = df_cadastro['Código'].astype(str) + " - " + df_cadastro['Sabor'].astype(str)
                produto_sel = col1.selectbox("Produto", lista_p)
                
                qtd = col2.number_input("Quantidade", min_value=1, step=1)
                dt = col2.date_input("Data", date.today())
                obs = st.text_input("Observação/Cliente")
                
                if st.form_submit_button("Confirmar Registro"):
                    # Aqui você pode instruir como salvar de volta manualmente na planilha 
                    # ou podemos configurar a API Key caso queira automação total de escrita.
                    st.info("Para salvar: Copie os dados abaixo e cole na sua Planilha Google na aba 'movimentacoes'.")
                    
                    cod = str(produto_sel).split(" - ")[0]
                    dados_p = df_cadastro[df_cadastro['Código'].astype(str) == cod].iloc[0]
                    preco_ref = dados_p['Preço Venda'] if "Saída" in tipo else dados_p['Valor Pago']
                    total = float(str(preco_ref).replace(',', '.')) * qtd
                    
                    dados_linha = f"{dt.strftime('%d/%m/%Y')};{tipo};{cod};{qtd};{total};Por: {st.session_state.usuario_atual} | {obs}"
                    st.code(dados_linha)
                    st.success("Linha gerada! Basta colar no final da sua planilha.")

    # --- TELA: BALANÇO FINANCEIRO ---
    elif opcao == "Balanço Financeiro":
        st.header("📊 Balanço Financeiro")
        if df_movimentacoes.empty:
            st.info("Adicione dados na aba 'movimentacoes' da sua Planilha Google.")
        else:
            investido = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Entrada', na=False)]['Valor Total'].sum()
            vendas = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Saída', na=False)]['Valor Total'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Investido", f"R$ {investido:.2f}")
            c2.metric("Total de Vendas", f"R$ {vendas:.2f}")
            c3.metric("Faturamento (Resultado)", f"R$ {vendas - investido:.2f}", delta=f"{vendas - investido:.2f}")
            
            st.divider()
            st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

    # --- TELA: ESTOQUE ---
    elif opcao == "Painel de Estoque":
        st.header("📦 Estoque Atual")
        if not df_movimentacoes.empty:
            ent = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Entrada', na=False)].groupby('Código')['Quantidade'].sum().reset_index(name='E')
            sai = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Saída', na=False)].groupby('Código')['Quantidade'].sum().reset_index(name='S')
            stk = pd.merge(df_cadastro[['Código', 'Sabor']], ent, on='Código', how='left').fillna(0)
            stk = pd.merge(stk, sai, on='Código', how='left').fillna(0)
            stk['Estoque'] = stk['E'] - stk['S']
            st.dataframe(stk[['Código', 'Sabor', 'Estoque']], use_container_width=True, hide_index=True)

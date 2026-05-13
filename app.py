import streamlit as st
import pandas as pd
from datetime import date

# --- CONFIGURAÇÕES DO SISTEMA ---
st.set_page_config(page_title="Gestão de Marmitas", layout="wide")

# Identificação da sua Planilha Google
ID_PLANILHA = "1rjxVMvNuok2KN2aO2hJGtuCtb2R0YCPwdx9TiS74e3o"

# Links de exportação direta (utilizando os GIDs que você forneceu)
URL_CADASTRO = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid=485394711"
URL_MOVIMENTACOES = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid=0"

# Controle de Usuários
USUARIOS = {
    "Lidiane": "1234",
    "Mateus": "4321"
}

# --- FUNÇÕES DE DADOS ---
def ler_dados():
    try:
        # Lê os dados da planilha. sep=None identifica automaticamente se é vírgula ou ponto e vírgula
        df_c = pd.read_csv(URL_CADASTRO, sep=None, engine='python', encoding='utf-8')
        df_m = pd.read_csv(URL_MOVIMENTACOES, sep=None, engine='python', encoding='utf-8')
    except:
        # Fallback para outro tipo de codificação caso o Google mude o padrão
        df_c = pd.read_csv(URL_CADASTRO, sep=None, engine='python', encoding='latin-1')
        df_m = pd.read_csv(URL_MOVIMENTACOES, sep=None, engine='python', encoding='latin-1')
    
    # Limpeza profunda dos nomes das colunas (remove espaços e caracteres invisíveis)
    df_c.columns = [str(c).strip().replace('ï»¿', '').replace('\ufeff', '') for c in df_c.columns]
    df_m.columns = [str(c).strip().replace('ï»¿', '').replace('\ufeff', '') for c in df_m.columns]
    
    return df_c, df_m

# --- SISTEMA DE LOGIN ---
def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None

    if not st.session_state.autenticado:
        st.title("🔐 Acesso ao Sistema de Marmitas")
        user_select = st.selectbox("Quem está acessando?", list(USUARIOS.keys()))
        senha = st.text_input("Sua senha:", type="password")
        
        if st.button("Entrar"):
            if USUARIOS.get(user_select) == senha:
                st.session_state.autenticado = True
                st.session_state.usuario_atual = user_select
                st.rerun()
            else:
                st.error("Senha incorreta!")
        return False
    return True

# --- INÍCIO DO APLICATIVO ---
if login():
    # Carrega os dados da Planilha Google
    df_cadastro, df_movimentacoes = ler_dados()
    
    st.sidebar.title(f"Bem-vinda(o), {st.session_state.usuario_atual}!")
    opcao = st.sidebar.radio("Navegação:", ["Nova Venda/Produção", "Painel de Estoque", "Balanço Financeiro", "Cadastro de Produtos", "Sair"])

    if opcao == "Sair":
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.rerun()

    # --- TELA: NOVA VENDA/PRODUÇÃO ---
    if opcao == "Nova Venda/Produção":
        st.header("🛒 Registrar Operação")
        if df_cadastro.empty:
            st.warning("A lista de produtos está vazia na planilha.")
        else:
            with st.form("form_registro", clear_on_submit=True):
                col1, col2 = st.columns(2)
                tipo = col1.selectbox("Tipo de Movimento", ["Saída (Venda)", "Entrada (Produção)"])
                
                # Cria a lista de seleção baseada no cadastro
                opcoes_produtos = df_cadastro['Código'].astype(str) + " - " + df_cadastro['Sabor'].astype(str)
                produto_selecionado = col1.selectbox("Selecione o Produto", opcoes_produtos)
                
                quantidade = col2.number_input("Quantidade", min_value=1, step=1)
                data_mov = col2.date_input("Data da Operação", date.today())
                obs_extra = st.text_input("Observação ou Nome do Cliente")
                
                if st.form_submit_button("Gerar Linha para Planilha"):
                    cod = str(produto_selecionado).split(" - ")[0]
                    dados_p = df_cadastro[df_cadastro['Código'].astype(str) == cod].iloc[0]
                    
                    # Define qual preço usar baseado no tipo de movimento
                    preco_un = dados_p['Preço Venda'] if "Saída" in tipo else dados_p['Valor Pago']
                    total_calculado = float(str(preco_un).replace(',', '.')) * quantidade
                    
                    # Monta a linha pronta para ser colada na planilha
                    log_user = f"Por: {st.session_state.usuario_atual}"
                    if obs_extra: log_user += f" | {obs_extra}"
                    
                    linha_csv = f"{data_mov.strftime('%d/%m/%Y')};{tipo};{cod};{quantidade};{total_calculado:.2f};{log_user}"
                    
                    st.success("Operação processada! Copie a linha abaixo e cole na aba 'movimentacoes' da sua Planilha Google:")
                    st.code(linha_csv)

    # --- TELA: PAINEL DE ESTOQUE ---
    elif opcao == "Painel de Estoque":
        st.header("📦 Estoque Atual")
        if df_movimentacoes.empty:
            st.info("Nenhuma movimentação encontrada na planilha.")
        else:
            # Garante que os tipos são strings limpas para o filtro
            df_m = df_movimentacoes.copy()
            df_m['Tipo'] = df_m['Tipo'].astype(str).str.strip()
            
            ent = df_m[df_m['Tipo'].str.contains('Entrada', na=False)].groupby('Código')['Quantidade'].sum().reset_index(name='E')
            sai = df_m[df_m['Tipo'].str.contains('Saída', na=False)].groupby('Código')['Quantidade'].sum().reset_index(name='S')
            
            stk = pd.merge(df_cadastro[['Código', 'Sabor']], ent, on='Código', how='left').fillna(0)
            stk = pd.merge(stk, sai, on='Código', how='left').fillna(0)
            stk['Estoque'] = stk['E'] - stk['S']
            
            st.dataframe(stk[['Código', 'Sabor', 'Estoque']], use_container_width=True, hide_index=True)

    # --- TELA: BALANÇO FINANCEIRO ---
    elif opcao == "Balanço Financeiro":
        st.header("📊 Resultado Financeiro")
        if df_movimentacoes.empty:
            st.info("Adicione dados na planilha para visualizar o balanço.")
        else:
            # Soma de todo o valor gasto nas Entradas (Investimento)
            valor_investido = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Entrada', na=False)]['Valor Total'].sum()
            # Soma de todo o valor recebido nas Saídas (Vendas)
            valor_vendas = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Saída', na=False)]['Valor Total'].sum()
            # Faturamento Real = Vendas - Investimento
            faturamento_real = valor_vendas - valor_investido

            c1, c2, c3 = st.columns(3)
            c1.metric("Valor Pago (Investimento)", f"R$ {valor_investido:.2f}")
            c2.metric("Valor das Vendas (Bruto)", f"R$ {valor_vendas:.2f}")
            c3.metric("Faturamento (Resultado)", f"R$ {faturamento_real:.2f}", delta=f"{faturamento_real:.2f}")

            st.divider()
            st.subheader("Histórico de Movimentações (Lido do Google Sheets)")
            st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

    # --- TELA: CADASTRO DE PRODUTOS ---
    elif opcao == "Cadastro de Produtos":
        st.header("📝 Produtos Cadastrados")
        if df_cadastro.empty:
            st.info("Nenhum produto cadastrado na aba 'cadastro'.")
        else:
            st.dataframe(df_cadastro, use_container_width=True, hide_index=True)
            st.info("Para cadastrar ou alterar produtos, edite diretamente a aba 'cadastro' na sua Planilha Google.")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Gestão de Marmitas", layout="wide", page_icon="🍱")

# --- CONTROLE DE ACESSO ---
USUARIOS = {
    "Lidiane": "1234",
    "Mateus": "4321"
}

def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None

    if not st.session_state.autenticado:
        st.title("🔐 Acesso ao Sistema")
        col_l, col_r = st.columns([1, 1])
        with col_l:
            user_select = st.selectbox("Selecione o usuário:", list(USUARIOS.keys()))
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

# --- SISTEMA PÓS-LOGIN ---
if login():
    # Conecta ao Google Sheets usando as Secrets [connections.gsheets]
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Carregamento de dados (ttl=0 evita que o app mostre dados antigos do cache)
    try:
        df_cadastro = conn.read(worksheet="cadastro", ttl=0)
        df_movimentacoes = conn.read(worksheet="movimentacoes", ttl=0)
    except Exception as e:
        st.error("Erro de conexão com a planilha. Verifique as Secrets e o compartilhamento.")
        st.stop()

    # Barra Lateral
    st.sidebar.title(f"👤 {st.session_state.usuario_atual}")
    opcao = st.sidebar.radio("Navegação:", ["Nova Venda/Produção", "Painel de Estoque", "Balanço Financeiro", "Cadastro de Produtos", "Sair"])

    if opcao == "Sair":
        st.session_state.autenticado = False
        st.rerun()

    # --- TELA 1: REGISTRAR OPERAÇÃO ---
    if opcao == "Nova Venda/Produção":
        st.header("🛒 Registrar Operação")
        
        if df_cadastro.empty:
            st.warning("Nenhum produto cadastrado na aba 'cadastro' da planilha.")
        else:
            with st.form("form_registro", clear_on_submit=True):
                c1, c2 = st.columns(2)
                tipo = c1.selectbox("Tipo de Movimento", ["Saída (Venda)", "Entrada (Produção)"])
                
                # Monta lista de seleção: "Código - Sabor"
                opcoes_prod = df_cadastro['Código'].astype(str) + " - " + df_cadastro['Sabor'].astype(str)
                produto_sel = c1.selectbox("Produto", opcoes_prod)
                
                qtd = c2.number_input("Quantidade", min_value=1, step=1)
                data_mov = c2.date_input("Data", date.today())
                obs = st.text_input("Observação / Nome do Cliente")
                
                if st.form_submit_button("Confirmar e Salvar na Planilha"):
                    # Extrai o código do produto selecionado
                    cod_selecionado = str(produto_sel).split(" - ")[0]
                    dados_p = df_cadastro[df_cadastro['Código'].astype(str) == cod_selecionado].iloc[0]
                    
                    # Define preço unitário: Preço Venda para Saídas, Valor Pago para Entradas
                    preco_un = dados_p['Preço Venda'] if "Saída" in tipo else dados_p['Valor Pago']
                    total = float(preco_un) * qtd
                    
                    # Cria a nova linha para adicionar
                    nova_linha = pd.DataFrame([{
                        "Data": data_mov.strftime("%d/%m/%Y"),
                        "Tipo": tipo,
                        "Código": cod_selecionado,
                        "Quantidade": qtd,
                        "Valor Total": total,
                        "Cliente/Obs": f"Por: {st.session_state.usuario_atual} | {obs}"
                    }])
                    
                    # Junta com as movimentações existentes e faz o upload
                    df_final = pd.concat([df_movimentacoes, nova_linha], ignore_index=True)
                    conn.update(worksheet="movimentacoes", data=df_final)
                    
                    st.success(f"✅ Registrado com sucesso: {qtd} un. de {cod_selecionado}")
                    st.rerun()

    # --- TELA 2: PAINEL DE ESTOQUE ---
    elif opcao == "Painel de Estoque":
        st.header("📦 Estoque Atual")
        if df_movimentacoes.empty:
            st.info("Nenhuma movimentação registrada.")
        else:
            # Cálculos de Entrada vs Saída
            ent = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Entrada', na=False)].groupby('Código')['Quantidade'].sum().reset_index(name='E')
            sai = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Saída', na=False)].groupby('Código')['Quantidade'].sum().reset_index(name='S')
            
            stk = pd.merge(df_cadastro[['Código', 'Sabor']], ent, on='Código', how='left').fillna(0)
            stk = pd.merge(stk, sai, on='Código', how='left').fillna(0)
            stk['Estoque'] = stk['E'] - stk['S']
            
            st.dataframe(stk[['Código', 'Sabor', 'Estoque']], use_container_width=True, hide_index=True)

    # --- TELA 3: BALANÇO FINANCEIRO ---
    elif opcao == "Balanço Financeiro":
        st.header("📊 Balanço Financeiro")
        if df_movimentacoes.empty:
            st.info("Sem dados financeiros.")
        else:
            # Investimento = Valor Total das Entradas
            investido = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Entrada', na=False)]['Valor Total'].sum()
            # Vendas = Valor Total das Saídas
            vendas = df_movimentacoes[df_movimentacoes['Tipo'].str.contains('Saída', na=False)]['Valor Total'].sum()
            faturamento = vendas - investido

            m1, m2, m3 = st.columns(3)
            m1.metric("Valor Pago (Investido)", f"R$ {investido:.2f}")
            m2.metric("Valor das Vendas", f"R$ {vendas:.2f}")
            m3.metric("Faturamento (Resultado)", f"R$ {faturamento:.2f}", delta=f"{faturamento:.2f}")

            st.divider()
            st.subheader("Histórico de Lançamentos")
            st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

    # --- TELA 4: PRODUTOS ---
    elif opcao == "Cadastro de Produtos":
        st.header("📝 Produtos no Sistema")
        st.dataframe(df_cadastro, use_container_width=True, hide_index=True)
        st.info("Dica: Para alterar preços ou adicionar sabores, edite a aba 'cadastro' diretamente no Google Sheets.")

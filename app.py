import streamlit as st
import pandas as pd
from datetime import date
import os

# ------------------------------------------------
# CONFIGURAÇÕES E USUÁRIOS
# ------------------------------------------------
st.set_page_config(page_title="Gestão de Marmitas", layout="wide")

# Dicionário de usuários e senhas
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
    ARQ_CADASTRO = 'cadastro.csv'
    ARQ_MOVIMENTACOES = 'movimentacoes.csv'

    def ler_dados_seguro(nome_arquivo, colunas_padrao):
        if not os.path.exists(nome_arquivo):
            df = pd.DataFrame(columns=colunas_padrao)
            df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig', sep=';')
            return df
        try:
            df = pd.read_csv(nome_arquivo, sep=';', encoding='utf-8-sig', engine='python', on_bad_lines='skip')
        except:
            df = pd.read_csv(nome_arquivo, sep=',', encoding='latin-1', engine='python', on_bad_lines='skip')
        
        df.columns = [str(c).strip().replace('ï»¿', '').replace('\ufeff', '') for c in df.columns]
        for col in colunas_padrao:
            if col not in df.columns:
                df[col] = 0
        return df

    df_cadastro = ler_dados_seguro(ARQ_CADASTRO, ['Código', 'Sabor', 'Preço Venda', 'Valor Pago'])
    df_movimentacoes = ler_dados_seguro(ARQ_MOVIMENTACOES, ['Data', 'Tipo', 'Código', 'Quantidade', 'Valor Total', 'Cliente/Obs'])

    # Barra lateral com identificação do usuário
    st.sidebar.title(f"Olá, {st.session_state.usuario_atual}!")
    opcao = st.sidebar.radio("Navegação:", ["Nova Venda/Produção", "Painel de Estoque", "Balanço Financeiro", "Cadastro de Produtos", "Sair"])

    if opcao == "Sair":
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.rerun()

    # ------------------------------------------------
    # TELA: NOVA VENDA/PRODUÇÃO (COM REGISTRO DE USUÁRIO)
    # ------------------------------------------------
    if opcao == "Nova Venda/Produção":
        st.header("🛒 Registrar Venda ou Produção")
        if df_cadastro.empty:
            st.warning("Cadastre os produtos primeiro.")
        else:
            with st.form("form_venda", clear_on_submit=True):
                col1, col2 = st.columns(2)
                tipo = col1.selectbox("Tipo", ["Saída (Venda)", "Entrada (Produção)"])
                lista_p = df_cadastro['Código'].astype(str) + " - " + df_cadastro['Sabor'].astype(str)
                produto = col1.selectbox("Produto", lista_p)
                qtd = col2.number_input("Quantidade", min_value=1, step=1)
                dt = col2.date_input("Data", date.today())
                obs_adicional = st.text_input("Observação/Cliente (Opcional)")
                
                if st.form_submit_button("Confirmar Registro"):
                    cod = str(produto).split(" - ")[0]
                    dados_p = df_cadastro[df_cadastro['Código'].astype(str) == cod].iloc[0]
                    
                    preco_ref = dados_p['Preço Venda'] if "Saída" in tipo else dados_p['Valor Pago']
                    valor_u = float(str(preco_ref).replace(',', '.'))
                    total = valor_u * qtd
                    
                    # Identifica quem fez a ação no histórico
                    log_usuario = f"Por: {st.session_state.usuario_atual}"
                    if obs_adicional:
                        log_usuario += f" | Obs: {obs_adicional}"
                    
                    novo = pd.DataFrame([{
                        'Data': dt.strftime("%d/%m/%Y"),
                        'Tipo': "Saída" if "Saída" in tipo else "Entrada",
                        'Código': cod,
                        'Quantidade': qtd,
                        'Valor Total': round(total, 2),
                        'Cliente/Obs': log_usuario
                    }])
                    novo.to_csv(ARQ_MOVIMENTACOES, mode='a', header=False, index=False, encoding='utf-8-sig', sep=';')
                    st.success(f"Registrado por {st.session_state.usuario_atual}!")
                    st.rerun()

    # ------------------------------------------------
    # TELA: BALANÇO FINANCEIRO
    # ------------------------------------------------
    elif opcao == "Balanço Financeiro":
        st.header("📊 Balanço Financeiro")
        if df_movimentacoes.empty:
            st.info("Sem dados para exibir.")
        else:
            valor_investido = df_movimentacoes[df_movimentacoes['Tipo'] == 'Entrada']['Valor Total'].sum()
            valor_vendas = df_movimentacoes[df_movimentacoes['Tipo'] == 'Saída']['Valor Total'].sum()
            faturamento_real = valor_vendas - valor_investido

            c1, c2, c3 = st.columns(3)
            c1.metric("Valor Investido (Compra)", f"R$ {valor_investido:.2f}")
            c2.metric("Valor das Vendas", f"R$ {valor_vendas:.2f}")
            c3.metric("Faturamento (Resultado)", f"R$ {faturamento_real:.2f}", delta=f"{faturamento_real:.2f}")

            st.divider()
            st.subheader("Histórico Detalhado (Quem fez o quê)")
            # Mostra a tabela com a coluna Cliente/Obs onde está o nome do usuário
            st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

    # ... (As outras telas permanecem iguais)
    elif opcao == "Painel de Estoque":
        st.header("📦 Controle de Estoque")
        if not df_movimentacoes.empty:
            df_m = df_movimentacoes.copy()
            df_c = df_cadastro.copy()
            ent = df_m[df_m['Tipo'] == 'Entrada'].groupby('Código')['Quantidade'].sum().reset_index(name='Entradas')
            sai = df_m[df_m['Tipo'] == 'Saída'].groupby('Código')['Quantidade'].sum().reset_index(name='Saídas')
            stk = pd.merge(df_c[['Código', 'Sabor']], ent, on='Código', how='left').fillna(0)
            stk = pd.merge(stk, sai, on='Código', how='left').fillna(0)
            stk['Estoque Atual'] = stk['Entradas'] - stk['Saídas']
            st.dataframe(stk, use_container_width=True, hide_index=True)

    elif opcao == "Cadastro de Produtos":
        st.header("📝 Gestão de Produtos")
        with st.form("cad_novo"):
            c1, c2 = st.columns(2)
            cod_n = c1.text_input("Código")
            sab_n = c2.text_input("Sabor")
            c3, c4 = st.columns(2)
            pre_v = c3.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
            pre_p = c4.number_input("Valor Pago (Custo Unitário)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Salvar"):
                if cod_n and sab_n:
                    novo_p = pd.DataFrame([{'Código': cod_n, 'Sabor': sab_n, 'Preço Venda': pre_v, 'Valor Pago': pre_p}])
                    novo_p.to_csv(ARQ_CADASTRO, mode='a', header=False, index=False, encoding='utf-8-sig', sep=';')
                    st.success("Salvo!")
                    st.rerun()
        st.dataframe(df_cadastro, use_container_width=True, hide_index=True)
        

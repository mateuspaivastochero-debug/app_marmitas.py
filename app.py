import streamlit as st
import pandas as pd
from datetime import date
import os

# ------------------------------------------------
# CONFIGURAÇÕES E SEGURANÇA
# ------------------------------------------------
st.set_page_config(page_title="Gestão de Marmitas", layout="wide")

# Defina sua senha aqui
SENHA_ACESSO = "1234" 

def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔐 Acesso ao Sistema")
        senha = st.text_input("Digite a senha para entrar:", type="password")
        if st.button("Entrar"):
            if senha == SENHA_ACESSO:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
        return False
    return True

if login():
    ARQ_CADASTRO = 'cadastro.csv'
    ARQ_MOVIMENTACOES = 'movimentacoes.csv'

    # Função blindada para ler dados
    def ler_dados_seguro(nome_arquivo, colunas_padrao):
        if not os.path.exists(nome_arquivo):
            df = pd.DataFrame(columns=colunas_padrao)
            df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig', sep=';')
            return df
        try:
            df = pd.read_csv(nome_arquivo, sep=';', encoding='utf-8-sig', engine='python', on_bad_lines='skip')
            if len(df.columns) <= 1:
                df = pd.read_csv(nome_arquivo, sep=',', encoding='utf-8-sig', engine='python', on_bad_lines='skip')
        except:
            df = pd.read_csv(nome_arquivo, sep=',', encoding='latin-1', engine='python', on_bad_lines='skip')
        
        df.columns = [str(c).strip().replace('ï»¿', '').replace('\ufeff', '') for c in df.columns]
        return df

    df_cadastro = ler_dados_seguro(ARQ_CADASTRO, ['Código', 'Sabor', 'Preço Venda'])
    df_movimentacoes = ler_dados_seguro(ARQ_MOVIMENTACOES, ['Data', 'Tipo', 'Código', 'Quantidade', 'Valor Total', 'Cliente/Obs'])

    # ------------------------------------------------
    # MENU LATERAL
    # ------------------------------------------------
    st.sidebar.title("Sistema de Marmitas")
    opcao = st.sidebar.radio("Navegação:", ["Nova Venda/Produção", "Painel de Estoque", "Balanço Financeiro", "Cadastro de Produtos", "Sair"])

    if opcao == "Sair":
        st.session_state.autenticado = False
        st.rerun()

    # ------------------------------------------------
    # TELA 1: REGISTRAR MOVIMENTAÇÃO
    # ------------------------------------------------
    if opcao == "Nova Venda/Produção":
        st.header("🛒 Registrar Venda ou Produção")
        if df_cadastro.empty:
            st.warning("Cadastre os produtos primeiro.")
        else:
            with st.form("form_venda", clear_on_submit=True):
                c1, c2 = st.columns(2)
                tipo = c1.selectbox("Tipo", ["Saída (Venda)", "Entrada (Produção)"])
                lista_p = df_cadastro['Código'].astype(str) + " - " + df_cadastro['Sabor'].astype(str)
                produto = c1.selectbox("Produto", lista_p)
                qtd = c2.number_input("Quantidade", min_value=1, step=1)
                dt = c2.date_input("Data", date.today())
                obs = st.text_input("Observação/Cliente")
                
                if st.form_submit_button("Confirmar Registro"):
                    cod = str(produto).split(" - ")[0]
                    preco = df_cadastro.loc[df_cadastro['Código'].astype(str) == cod, 'Preço Venda'].values[0]
                    valor_u = float(str(preco).replace(',', '.'))
                    total = valor_u * qtd
                    
                    novo = pd.DataFrame([{
                        'Data': dt.strftime("%d/%m/%Y"),
                        'Tipo': "Saída" if "Saída" in tipo else "Entrada",
                        'Código': cod,
                        'Quantidade': qtd,
                        'Valor Total': round(total, 2),
                        'Cliente/Obs': obs
                    }])
                    novo.to_csv(ARQ_MOVIMENTACOES, mode='a', header=False, index=False, encoding='utf-8-sig', sep=';')
                    st.success(f"Registrado! Total: R$ {total:.2f}")

    # ------------------------------------------------
    # TELA 2: PAINEL DE ESTOQUE
    # ------------------------------------------------
    elif opcao == "Painel de Estoque":
        st.header("📦 Controle de Estoque")
        if not df_movimentacoes.empty:
            df_m = df_movimentacoes.copy()
            df_c = df_cadastro.copy()
            df_m['Código'] = df_m['Código'].astype(str)
            df_c['Código'] = df_c['Código'].astype(str)
            
            ent = df_m[df_m['Tipo'] == 'Entrada'].groupby('Código')['Quantidade'].sum().reset_index(name='Entradas')
            sai = df_m[df_m['Tipo'] == 'Saída'].groupby('Código')['Quantidade'].sum().reset_index(name='Saídas')
            
            stk = pd.merge(df_c[['Código', 'Sabor']], ent, on='Código', how='left').fillna(0)
            stk = pd.merge(stk, sai, on='Código', how='left').fillna(0)
            stk['Estoque Atual'] = stk['Entradas'] - stk['Saídas']
            st.dataframe(stk, use_container_width=True, hide_index=True)

    # ------------------------------------------------
    # TELA 3: BALANÇO FINANCEIRO (NOVA)
    # ------------------------------------------------
    elif opcao == "Balanço Financeiro":
        st.header("📊 Balanço de Entradas e Saídas")
        if df_movimentacoes.empty:
            st.info("Ainda não há dados financeiros.")
        else:
            # Cálculos Rápidos
            total_vendas = df_movimentacoes[df_movimentacoes['Tipo'] == 'Saída']['Valor Total'].sum()
            total_produzido = df_movimentacoes[df_movimentacoes['Tipo'] == 'Entrada']['Quantidade'].sum()
            total_vendido = df_movimentacoes[df_movimentacoes['Tipo'] == 'Saída']['Quantidade'].sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento Total", f"R$ {total_vendas:.2f}")
            m2.metric("Marmitas Produzidas", int(total_produzido))
            m3.metric("Marmitas Vendidas", int(total_vendido))

            st.subheader("Histórico de Fluxo")
            st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

    # ------------------------------------------------
    # TELA 4: CADASTRO DE PRODUTOS
    # ------------------------------------------------
    elif opcao == "Cadastro de Produtos":
        st.header("📝 Gestão de Produtos")
        with st.form("cad_novo"):
            c1, c2, c3 = st.columns([1, 2, 1])
            cod_n = c1.text_input("Código")
            sab_n = c2.text_input("Sabor")
            pre_n = c3.number_input("Preço", min_value=0.0, format="%.2f")
            if st.form_submit_button("Salvar"):
                if cod_n and sab_n:
                    novo_p = pd.DataFrame([{'Código': cod_n, 'Sabor': sab_n, 'Preço Venda': pre_n}])
                    novo_p.to_csv(ARQ_CADASTRO, mode='a', header=False, index=False, encoding='utf-8-sig', sep=';')
                    st.success("Produto salvo!")
                    st.rerun()
        st.dataframe(df_cadastro, use_container_width=True)

import streamlit as st
import pandas as pd
from datetime import date
import os

# ------------------------------------------------
# CONFIGURAÇÕES E SEGURANÇA
# ------------------------------------------------
st.set_page_config(page_title="Gestão de Marmitas", layout="wide")

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
        # Garante que colunas novas existam se o arquivo for antigo
        for col in colunas_padrao:
            if col not in df.columns:
                df[col] = 0
        return df

    # Agora incluímos 'Valor Pago' no cadastro
    df_cadastro = ler_dados_seguro(ARQ_CADASTRO, ['Código', 'Sabor', 'Preço Venda', 'Valor Pago'])
    df_movimentacoes = ler_dados_seguro(ARQ_MOVIMENTACOES, ['Data', 'Tipo', 'Código', 'Quantidade', 'Valor Total', 'Cliente/Obs'])

    st.sidebar.title("Sistema de Marmitas")
    opcao = st.sidebar.radio("Navegação:", ["Nova Venda/Produção", "Painel de Estoque", "Balanço Financeiro", "Cadastro de Produtos", "Sair"])

    if opcao == "Sair":
        st.session_state.autenticado = False
        st.rerun()

    # ------------------------------------------------
    # TELA: NOVA VENDA/PRODUÇÃO
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
                    dados_p = df_cadastro[df_cadastro['Código'].astype(str) == cod].iloc[0]
                    
                    # Usa preço de venda para Saídas e valor pago para Entradas (Custo)
                    preco_ref = dados_p['Preço Venda'] if "Saída" in tipo else dados_p['Valor Pago']
                    valor_u = float(str(preco_ref).replace(',', '.'))
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
                    st.success(f"Registrado! Valor Processado: R$ {total:.2f}")

    # ------------------------------------------------
    # TELA: BALANÇO FINANCEIRO (ATUALIZADA)
    # ------------------------------------------------
    elif opcao == "Balanço Financeiro":
        st.header("📊 Balanço Financeiro e Lucratividade")
        if df_movimentacoes.empty:
            st.info("Sem dados.")
        else:
            # Faturamento (Vendas)
            vendas = df_movimentacoes[df_movimentacoes['Tipo'] == 'Saída']
            faturamento = vendas['Valor Total'].sum()
            
            # Custo (Baseado no Valor Pago cadastrado para cada item vendido)
            df_custos = pd.merge(vendas, df_cadastro[['Código', 'Valor Pago']], on='Código', how='left')
            df_custos['Custo Total'] = df_custos['Quantidade'] * df_custos['Valor Pago'].astype(float)
            custo_total_vendas = df_custos['Custo Total'].sum()
            
            lucro = faturamento - custo_total_vendas

            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento (Vendas)", f"R$ {faturamento:.2f}")
            m2.metric("Custo das Vendas", f"R$ {custo_total_vendas:.2f}", delta_color="inverse")
            m3.metric("Lucro Estimado", f"R$ {lucro:.2f}", delta=f"{lucro:.2f}")

            st.subheader("Detalhamento de Movimentações")
            st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

    # ------------------------------------------------
    # TELA: CADASTRO (COM VALOR PAGO)
    # ------------------------------------------------
    elif opcao == "Cadastro de Produtos":
        st.header("📝 Gestão de Produtos")
        with st.form("cad_novo"):
            c1, c2 = st.columns(2)
            cod_n = c1.text_input("Código")
            sab_n = c2.text_input("Sabor")
            c3, c4 = st.columns(2)
            pre_v = c3.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
            pre_p = c4.number_input("Valor Pago/Custo (R$)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("Salvar Produto"):
                if cod_n and sab_n:
                    novo_p = pd.DataFrame([{'Código': cod_n, 'Sabor': sab_n, 'Preço Venda': pre_v, 'Valor Pago': pre_p}])
                    novo_p.to_csv(ARQ_CADASTRO, mode='a', header=False, index=False, encoding='utf-8-sig', sep=';')
                    st.success("Produto salvo!")
                    st.rerun()
        st.subheader("Lista de Produtos e Custos")
        st.dataframe(df_cadastro, use_container_width=True, hide_index=True)

    # ... (Tela de estoque permanece igual)

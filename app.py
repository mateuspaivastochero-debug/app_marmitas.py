import streamlit as st
import pandas as pd
from datetime import date
import os

# ------------------------------------------------
# CONFIGURAÇÕES E CARREGAMENTO DE DADOS
# ------------------------------------------------
st.set_page_config(page_title="Gestão de Marmitas", layout="wide")

ARQ_CADASTRO = 'cadastro.csv'
ARQ_MOVIMENTACOES = 'movimentacoes.csv'

# Função para ler dados garantindo que as colunas não se misturam
def ler_dados_seguro(nome_arquivo, colunas_padrao):
    if not os.path.exists(nome_arquivo):
        df = pd.DataFrame(columns=colunas_padrao)
        df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig', sep=',')
        return df
    try:
        # Tenta ler com ponto e vírgula primeiro
        df = pd.read_csv(nome_arquivo, sep=';', encoding='utf-8-sig', engine='python', on_bad_lines='skip')
        # Se leu tudo numa coluna só, tenta com vírgula
        if len(df.columns) <= 1:
            df = pd.read_csv(nome_arquivo, sep=',', encoding='utf-8-sig', engine='python', on_bad_lines='skip')
    except:
        df = pd.read_csv(nome_arquivo, sep=',', encoding='latin-1', engine='python', on_bad_lines='skip')
    
    # Limpa nomes de colunas e remove espaços invisíveis
    df.columns = [str(c).strip().replace('ï»¿', '').replace('\ufeff', '') for c in df.columns]
    return df

# Inicializa os DataFrames
df_cadastro = ler_dados_seguro(ARQ_CADASTRO, ['Código', 'Sabor', 'Preço Venda'])
df_movimentacoes = ler_dados_seguro(ARQ_MOVIMENTACOES, ['Data', 'Tipo', 'Código', 'Quantidade', 'Valor Total', 'Cliente/Obs'])

# ------------------------------------------------
# MENU LATERAL
# ------------------------------------------------
st.sidebar.title("Menu do Sistema")
opcao = st.sidebar.radio("Navegação:", ["Nova Movimentação (Venda/Produção)", "Painel de Stock", "Cadastro de Produtos", "Ver Histórico"])

# ------------------------------------------------
# ECRÃ 1: REGISTAR NOVA MOVIMENTAÇÃO
# ------------------------------------------------
if opcao == "Nova Movimentação (Venda/Produção)":
    st.header("🛒 Registar Venda ou Nova Produção")
    
    if df_cadastro.empty or 'Código' not in df_cadastro.columns:
        st.warning("Cadastre os seus sabores primeiro no separador 'Cadastro de Produtos'.")
    else:
        with st.form("form_movimentacao", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo", ["Saída (Venda)", "Entrada (Produção)"])
                opcoes = df_cadastro['Código'].astype(str) + " - " + df_cadastro['Sabor'].astype(str)
                produto_sel = st.selectbox("Produto", opcoes)
            with col2:
                qtd = st.number_input("Quantidade", min_value=1, step=1)
                dt = st.date_input("Data", date.today())
                obs = st.text_input("Observação")
            
            if st.form_submit_button("Registar"):
                cod = str(produto_sel).split(" - ")[0]
                preco = df_cadastro.loc[df_cadastro['Código'].astype(str) == cod, 'Preço Venda'].values[0]
                
                # Converte preço para número se vier como texto do CSV
                val_unit = float(str(preco).replace(',', '.'))
                total = val_unit * qtd
                
                novo = pd.DataFrame([{
                    'Data': dt.strftime("%d/%m/%Y"),
                    'Tipo': "Saída" if "Saída" in tipo else "Entrada",
                    'Código': cod,
                    'Quantidade': qtd,
                    'Valor Total': round(total, 2),
                    'Cliente/Obs': obs
                }])
                
                novo.to_csv(ARQ_MOVIMENTACOES, mode='a', header=False, index=False, encoding='utf-8-sig', sep=';')
                st.success(f"Registado! Total: R$ {total:.2f}")
                st.rerun()

# ------------------------------------------------
# ECRÃ 2: PAINEL DE STOCK
# ------------------------------------------------
elif opcao == "Painel de Stock":
    st.header("📦 Stock Atual")
    if df_movimentacoes.empty:
        st.info("Sem movimentações.")
    else:
        # Garante que os códigos são strings para o cruzamento
        df_mov = df_movimentacoes.copy()
        df_cad = df_cadastro.copy()
        df_mov['Código'] = df_mov['Código'].astype(str)
        df_cad['Código'] = df_cad['Código'].astype(str)

        ent = df_mov[df_mov['Tipo'] == 'Entrada'].groupby('Código')['Quantidade'].sum().reset_index(name='Entradas')
        sai = df_mov[df_mov['Tipo'] == 'Saída'].groupby('Código')['Quantidade'].sum().reset_index(name='Saídas')
        
        stk = pd.merge(df_cad[['Código', 'Sabor']], ent, on='Código', how='left').fillna(0)
        stk = pd.merge(stk, sai, on='Código', how='left').fillna(0)
        stk['Stock Atual'] = stk['Entradas'] - stk['Saídas']
        
        st.dataframe(stk, use_container_width=True, hide_index=True)

# ------------------------------------------------
# ECRÃ 3: CADASTRO DE PRODUTOS
# ------------------------------------------------
elif opcao == "Cadastro de Produtos":
    st.header("📝 Novo Sabor")
    with st.form("cad_prod", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 2, 1])
        cod_n = c1.text_input("Código")
        sab_n = c2.text_input("Sabor")
        pre_n = c3.number_input("Preço", min_value=0.0, format="%.2f")
        if st.form_submit_button("Guardar"):
            if cod_n and sab_n:
                novo_p = pd.DataFrame([{'Código': cod_n, 'Sabor': sab_n, 'Preço Venda': pre_n}])
                novo_p.to_csv(ARQ_CADASTRO, mode='a', header=False, index=False, encoding='utf-8-sig', sep=';')
                st.success("Guardado!")
                st.rerun()
    st.dataframe(df_cadastro, use_container_width=True)

# ------------------------------------------------
# ECRÃ 4: HISTÓRICO
# ------------------------------------------------
elif opcao == "Ver Histórico":
    st.header("📄 Histórico Completo")
    st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

import streamlit as st
import pandas as pd
from datetime import date
import os

# ------------------------------------------------
# CONFIGURAÇÕES E CARREGAMENTO DE DADOS
# ------------------------------------------------
st.set_page_config(page_title="Gestão de Marmitas Fit", layout="wide")

ARQ_CADASTRO = 'cadastro.csv'
ARQ_MOVIMENTACOES = 'movimentacoes.csv'

# Cria os arquivos vazios se não existirem
if not os.path.exists(ARQ_CADASTRO):
    pd.DataFrame(columns=['Código', 'Sabor', 'Preço Venda']).to_csv(ARQ_CADASTRO, index=False)
if not os.path.exists(ARQ_MOVIMENTACOES):
    pd.DataFrame(columns=['Data', 'Tipo', 'Código', 'Quantidade', 'Valor Total', 'Cliente/Obs']).to_csv(ARQ_MOVIMENTACOES, index=False)

# Carrega os dados para o Pandas
df_cadastro = pd.read_csv(ARQ_CADASTRO)
df_movimentacoes = pd.read_csv(ARQ_MOVIMENTACOES)

# ------------------------------------------------
# MENU LATERAL
# ------------------------------------------------
st.sidebar.title("Menu do Sistema")
opcao = st.sidebar.radio("Navegação:", ["Nova Movimentação (Venda/Produção)", "Painel de Estoque", "Cadastro de Produtos", "Ver Histórico"])

# ------------------------------------------------
# TELA 1: REGISTRAR NOVA MOVIMENTAÇÃO
# ------------------------------------------------
if opcao == "Nova Movimentação (Venda/Produção)":
    st.header("🛒 Registrar Venda ou Nova Produção")
    
    if df_cadastro.empty:
        st.warning("Cadastre seus sabores primeiro na aba 'Cadastro de Produtos'.")
    else:
        with st.form("form_movimentacao", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                tipo = st.selectbox("Tipo de Movimento", ["Saída (Venda)", "Entrada (Produção)"])
                # Cria uma lista amigável com Código + Sabor para o vendedor escolher
                opcoes_produtos = df_cadastro['Código'] + " - " + df_cadastro['Sabor']
                produto_selecionado = st.selectbox("Produto", opcoes_produtos)
            
            with col2:
                quantidade = st.number_input("Quantidade", min_value=1, step=1)
                data_mov = st.date_input("Data", date.today())
                obs = st.text_input("Cliente / Observação (Opcional)")
                
            submit = st.form_submit_button("Registrar")
            
            if submit:
                # Extrai apenas o código (antes do hífen)
                codigo = produto_selecionado.split(" - ")[0]
                
                # Busca o preço de venda para calcular o total
                preco_venda = df_cadastro.loc[df_cadastro['Código'] == codigo, 'Preço Venda'].values[0]
                valor_total = float(preco_venda) * quantidade
                tipo_bd = "Saída" if "Saída" in tipo else "Entrada"
                
                novo_registro = pd.DataFrame([{
                    'Data': data_mov.strftime("%d/%m/%Y"),
                    'Tipo': tipo_bd,
                    'Código': codigo,
                    'Quantidade': quantidade,
                    'Valor Total': valor_total,
                    'Cliente/Obs': obs
                }])
                
                # Salva no arquivo
                novo_registro.to_csv(ARQ_MOVIMENTACOES, mode='a', header=False, index=False)
                st.success(f"Registrado com sucesso! Valor Total: R$ {valor_total:.2f}")

# ------------------------------------------------
# TELA 2: PAINEL DE ESTOQUE (Calculado Automaticamente)
# ------------------------------------------------
elif opcao == "Painel de Estoque":
    st.header("📦 Estoque Atual")
    
    if df_movimentacoes.empty:
        st.info("Nenhuma movimentação registrada ainda.")
    else:
        # Separa entradas e saídas
        entradas = df_movimentacoes[df_movimentacoes['Tipo'] == 'Entrada'].groupby('Código')['Quantidade'].sum().reset_index(name='Total Entradas')
        saidas = df_movimentacoes[df_movimentacoes['Tipo'] == 'Saída'].groupby('Código')['Quantidade'].sum().reset_index(name='Total Saídas')
        
        # Faz o cruzamento (Merge) das tabelas usando Pandas
        estoque = pd.merge(df_cadastro[['Código', 'Sabor']], entradas, on='Código', how='left')
        estoque = pd.merge(estoque, saidas, on='Código', how='left')
        
        # Preenche valores vazios com zero e calcula o estoque final
        estoque.fillna(0, inplace=True)
        estoque['Estoque Atual'] = estoque['Total Entradas'] - estoque['Total Saídas']
        
        # Formata para mostrar como números inteiros
        estoque[['Total Entradas', 'Total Saídas', 'Estoque Atual']] = estoque[['Total Entradas', 'Total Saídas', 'Estoque Atual']].astype(int)
        
        st.dataframe(estoque, use_container_width=True, hide_index=True)

# ------------------------------------------------
# TELA 3: CADASTRO DE PRODUTOS
# ------------------------------------------------
elif opcao == "Cadastro de Produtos":
    st.header("📝 Cadastrar Novo Sabor")
    
    with st.form("form_cadastro", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            codigo = st.text_input("Código (ex: H7)")
        with col2:
            sabor = st.text_input("Sabor / Descrição")
        with col3:
            preco = st.number_input("Preço de Venda (R$)", min_value=0.0, step=0.5, format="%.2f")
            
        submit = st.form_submit_button("Salvar Produto")
        
        if submit and codigo and sabor:
            novo_produto = pd.DataFrame([{'Código': codigo, 'Sabor': sabor, 'Preço Venda': preco}])
            novo_produto.to_csv(ARQ_CADASTRO, mode='a', header=False, index=False)
            st.success(f"Produto {codigo} cadastrado com sucesso!")
            
    st.subheader("Produtos Cadastrados")
    st.dataframe(df_cadastro, use_container_width=True, hide_index=True)

# ------------------------------------------------
# TELA 4: HISTÓRICO BRUTO
# ------------------------------------------------
elif opcao == "Ver Histórico":
    st.header("📄 Histórico de Movimentações")
    st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

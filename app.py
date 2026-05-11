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

# Cria os arquivos vazios se não existirem
if not os.path.exists(ARQ_CADASTRO):
    pd.DataFrame(columns=['Código', 'Sabor', 'Preço Venda']).to_csv(ARQ_CADASTRO, index=False, encoding='utf-8-sig')
if not os.path.exists(ARQ_MOVIMENTACOES):
    pd.DataFrame(columns=['Data', 'Tipo', 'Código', 'Quantidade', 'Valor Total', 'Cliente/Obs']).to_csv(ARQ_MOVIMENTACOES, index=False, encoding='utf-8-sig')

# Função blindada para ler os arquivos corrigindo caracteres e espaços invisíveis
def ler_arquivo_limpo(nome_arquivo):
    try:
        # Tenta ler no padrão do Brasil (ponto e vírgula) e UTF-8 limpo
        df = pd.read_csv(nome_arquivo, sep=';', encoding='utf-8-sig')
        if len(df.columns) < 2: 
            # Se falhar, tenta o padrão internacional (vírgula)
            df = pd.read_csv(nome_arquivo, sep=',', encoding='utf-8-sig')
    except:
        df = pd.read_csv(nome_arquivo, sep=',', encoding='latin-1')
    
    # HIGIENIZAÇÃO MÁXIMA: Remove espaços em branco e caracteres fantasmas das colunas
    df.columns = df.columns.str.replace('ï»¿', '').str.replace('\ufeff', '').str.strip()
    return df

# Carrega os dados higienizados
df_cadastro = ler_arquivo_limpo(ARQ_CADASTRO)
df_movimentacoes = ler_arquivo_limpo(ARQ_MOVIMENTACOES)

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
    
    # Verifica de forma segura se a coluna Código existe após a limpeza
    if df_cadastro.empty or 'Código' not in df_cadastro.columns:
        st.warning("Cadastre seus sabores primeiro na aba 'Cadastro de Produtos' ou verifique o arquivo cadastro.csv.")
    else:
        with st.form("form_movimentacao", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                tipo = st.selectbox("Tipo de Movimento", ["Saída (Venda)", "Entrada (Produção)"])
                # Força formato de texto para evitar quebras
                opcoes_produtos = df_cadastro['Código'].astype(str) + " - " + df_cadastro['Sabor'].astype(str)
                produto_selecionado = st.selectbox("Produto", opcoes_produtos)
            
            with col2:
                quantidade = st.number_input("Quantidade", min_value=1, step=1)
                data_mov = st.date_input("Data", date.today())
                obs = st.text_input("Cliente / Observação (Opcional)")
                
            submit = st.form_submit_button("Registrar")
            
            if submit:
                codigo = str(produto_selecionado).split(" - ")[0]
                preco_venda = df_cadastro.loc[df_cadastro['Código'].astype(str) == codigo, 'Preço Venda'].values[0]
                
                if isinstance(preco_venda, str):
                    preco_venda = preco_venda.replace(',', '.')
                
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
                
                novo_registro.to_csv(ARQ_MOVIMENTACOES, mode='a', header=False, index=False, encoding='utf-8-sig')
                st.success(f"Registrado com sucesso! Valor Total: R$ {valor_total:.2f}")

# ------------------------------------------------
# TELA 2: PAINEL DE ESTOQUE
# ------------------------------------------------
elif opcao == "Painel de Estoque":
    st.header("📦 Estoque Atual")
    
    if df_movimentacoes.empty or 'Código' not in df_movimentacoes.columns:
        st.info("Nenhuma movimentação registrada ainda.")
    else:
        df_movimentacoes['Código'] = df_movimentacoes['Código'].astype(str)
        df_cadastro['Código'] = df_cadastro['Código'].astype(str)
        
        entradas = df_movimentacoes[df_movimentacoes['Tipo'] == 'Entrada'].groupby('Código')['Quantidade'].sum().reset_index(name='Total Entradas')
        saidas = df_movimentacoes[df_movimentacoes['Tipo'] == 'Saída'].groupby('Código')['Quantidade'].sum().reset_index(name='Total Saídas')
        
        estoque = pd.merge(df_cadastro[['Código', 'Sabor']], entradas, on='Código', how='left')
        estoque = pd.merge(estoque, saidas, on='Código', how='left')
        
        estoque.fillna(0, inplace=True)
        estoque['Estoque Atual'] = estoque['Total Entradas'] - estoque['Total Saídas']
        
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
            novo_produto = pd.DataFrame([{'Código': str(codigo), 'Sabor': str(sabor), 'Preço Venda': preco}])
            novo_produto.to_csv(ARQ_CADASTRO, mode='a', header=False, index=False, encoding='utf-8-sig')
            st.success(f"Produto {codigo} cadastrado com sucesso!")
            
    st.subheader("Produtos Cadastrados")
    st.dataframe(df_cadastro, use_container_width=True, hide_index=True)

# ------------------------------------------------
# TELA 4: HISTÓRICO BRUTO
# ------------------------------------------------
elif opcao == "Ver Histórico":
    st.header("📄 Histórico de Movimentações")
    st.dataframe(df_movimentacoes, use_container_width=True, hide_index=True)

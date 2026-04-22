import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Sprint Dashboard Viewer", layout="wide", page_icon="📊")

# Função para limpar e processar os dados
def process_data(df):
    # Remover colunas inúteis se existirem
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # Limpar dados marcados com '*'
    df = df.replace({'\*': None}, regex=True)
    
    # Extrair apenas os números da coluna Story Point (Ex: "24 horas" vira 24)
    df['SP_Horas'] = df['Story Point'].astype(str).str.extract(r'(\d+)').astype(float)
    df['SP_Horas'] = df['SP_Horas'].fillna(0) # Se estiver vazio, considera 0 horas
    
    # Converter datas
    date_cols = ['Criado', 'Start date', 'Início dos testes', 'Resolvido', 'Início Sprint', 'Fim Sprint']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

    # Mapeamento de Status (Adaptado para o novo padrão do seu Excel)
    status_map = {
        'Concluído': 'Done', 'Itens concluídos': 'Done', 'Pronta para publicação': 'Done',
        'Em Desenvolvimento': 'In Progress', 'Em Teste': 'In Progress', 'Priorizada': 'Backlog',
        'Parking Lot': 'Backlog', 'Bloqueado': 'Blocked', 'Descartado': 'Cancelled', 'cancelado': 'Cancelled'
    }
    df['Status_Clean'] = df['Status'].map(status_map).fillna(df['Status'])

    return df

# Interface de Upload
st.title("📊 FastShop Dashboard Viewer")
st.markdown("Faça o upload do seu arquivo Excel exportado do Jira para visualizar as métricas da Sprint.")

uploaded_file = st.file_uploader("Escolha o arquivo Excel", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        df_raw = pd.read_excel(uploaded_file, engine='openpyxl')
        df = process_data(df_raw)
        
        # Filtros na Sidebar
        st.sidebar.header("Filtros")
        
        # Filtro de Sprint
        sprints = df['Sprint'].dropna().unique().tolist()
        selected_sprint = st.sidebar.selectbox("Selecione a Sprint", sprints)
        
        # Filtra apenas a sprint selecionada para o dashboard principal
        df_sprint = df[df['Sprint'] == selected_sprint]

        # Outros filtros
        clientes = df_sprint['Cliente'].dropna().unique().tolist()
        selected_cliente = st.sidebar.multiselect("Selecione o Cliente", clientes, default=clientes)
        
        tipos = df_sprint['Tipo de item'].dropna().unique().tolist()
        selected_tipos = st.sidebar.multiselect("Tipo de Item", tipos, default=tipos)

        # Aplicar Filtros
        df_filtered = df_sprint[df_sprint['Cliente'].isin(selected_cliente) & df_sprint['Tipo de item'].isin(selected_tipos)]

        # ========================================================
        # CÁLCULO DE SAÚDE E PREVISÃO DA SPRINT
        # ========================================================
        hoje = pd.Timestamp.now().normalize()
        inicio_sprint = df_filtered['Início Sprint'].min()
        fim_sprint = df_filtered['Fim Sprint'].max()

        total_horas = df_filtered['SP_Horas'].sum()
        done_items = df_filtered[df_filtered['Status_Clean'] == 'Done']
        horas_concluidas = done_items['SP_Horas'].sum()

        progresso_trabalho = (horas_concluidas / total_horas * 100) if total_horas > 0 else 0

        if pd.notna(inicio_sprint) and pd.notna(fim_sprint):
            dias_totais = (fim_sprint - inicio_sprint).days
            dias_passados = (hoje - inicio_sprint).days
            
            if dias_totais > 0:
                progresso_tempo = (dias_passados / dias_totais) * 100
                progresso_tempo = max(0, min(100, progresso_tempo)) # Limita entre 0 e 100
            else:
                progresso_tempo = 100 # Sprint de 1 dia ou já encerrada
                
            defasagem = progresso_tempo - progresso_trabalho
            
            if defasagem > 5: # Tolerância de 5%
                status_sprint = "EM ATRASO"
                cor_status = "🔴"
            elif defasagem > 0:
                status_sprint = "ATENÇÃO"
                cor_status = "🟡"
            else:
                status_sprint = "NO PRAZO"
                cor_status = "🟢"
        else:
            progresso_tempo = 0
            defasagem = 0
            status_sprint = "SEM DATAS"
            cor_status = "⚪"

        # ========================================================
        # LAYOUT DO DASHBOARD
        # ========================================================
        
        # Header da Sprint
        st.markdown(f"### Visão da Sprint: `{selected_sprint}`")
        if pd.notna(inicio_sprint) and pd.notna(fim_sprint):
            st.caption(f"Período: {inicio_sprint.strftime('%d/%m/%Y')} a {fim_sprint.strftime('%d/%m/%Y')}")

        # Indicadores Principais (KPIs)
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_bugs = len(df_filtered[df_filtered['Tipo de item'] == 'Bug'])
        qtd_itens = len(df_filtered)

        col1.metric("ESCOPO TOTAL (Horas)", f"{total_horas:.0f}h")
        col2.metric("HORAS ENTREGUES", f"{horas_concluidas:.0f}h")
        col3.metric("QTD DE ITENS", f"{qtd_itens}")
        col4.metric("TOTAL DE BUGS", f"{total_bugs}")
        
        # Coluna do Status de Atraso com cor
        with col5:
            st.metric("STATUS SPRINT", f"{cor_status} {status_sprint}")
            if status_sprint != "SEM DATAS":
                st.caption(f"Defasagem: {defasagem:.1f}%")

        # Barra de Progresso Visual
        st.markdown("#### Progresso da Sprint")
        prog_col1, prog_col2 = st.columns([3, 1])
        with prog_col1:
            st.progress(int(progresso_trabalho) / 100, text=f"Trabalho Entregue: {progresso_trabalho:.1f}%")
        with prog_col2:
            st.progress(int(progresso_tempo) / 100, text=f"Tempo Decorrido: {progresso_tempo:.1f}%")

        st.markdown("---")

        # Gráficos
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### Esforço por Status (Horas)")
            status_df = df_filtered.groupby('Status_Clean')['SP_Horas'].sum().reset_index()
            status_df = status_df.sort_values(by='SP_Horas', ascending=False)
            fig_status = px.bar(status_df, x='Status_Clean', y='SP_Horas', color='Status_Clean',
                               color_discrete_map={'Done': '#2ecc71', 'In Progress': '#3498db', 'Backlog': '#f39c12', 'Blocked': '#e74c3c'},
                               text_auto=True)
            fig_status.update_layout(xaxis_title="Status", yaxis_title="Horas", showlegend=False)
            st.plotly_chart(fig_status, use_container_width=True)

        with col_chart2:
            st.markdown("#### Mix de Atividades (Horas)")
            mix_df = df_filtered.groupby('Tipo de item')['SP_Horas'].sum().reset_index()
            fig_mix = px.pie(mix_df, values='SP_Horas', names='Tipo de item', hole=0.5,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_mix.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True)
            st.plotly_chart(fig_mix, use_container_width=True)

        col_chart3, col_chart4 = st.columns(2)

        with col_chart3:
            st.markdown("#### Distribuição de Tamanho dos Itens (Horas)")
            gran_df = df_filtered[df_filtered['SP_Horas'] > 0]
            if not gran_df.empty:
                fig_gran = px.histogram(gran_df, x="SP_Horas", nbins=10, 
                                       title="Quantidade de Cards por Carga de Horas",
                                       color_discrete_sequence=['#00b4d8'])
                fig_gran.update_layout(xaxis_title="Horas Estimadas (Story Points)", yaxis_title="Quantidade de Cards", bargap=0.2)
                st.plotly_chart(fig_gran, use_container_width=True)

        with col_chart4:
            st.markdown("#### Esforço por Cliente (Horas)")
            cliente_df = df_filtered.groupby('Cliente')['SP_Horas'].sum().reset_index()
            fig_cliente = px.bar(cliente_df, x='Cliente', y='SP_Horas', color='Cliente',
                                color_discrete_sequence=px.colors.qualitative.Vivid)
            fig_cliente.update_layout(showlegend=False, yaxis_title="Horas")
            st.plotly_chart(fig_cliente, use_container_width=True)

        # Tabela de Dados
        with st.expander("Ver Detalhes dos Itens da Sprint"):
            # Seleciona colunas relevantes para não poluir a tela
            cols_view = ['Tipo de item', 'Chave', 'Resumo', 'Status', 'Story Point', 'Cliente', 'Prioridade', 'Start date', 'Início dos testes', 'Resolvido']
            existing_cols = [c for c in cols_view if c in df_filtered.columns]
            st.dataframe(df_filtered[existing_cols].sort_values(by='Status'), use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Aguardando o upload do arquivo Excel...")

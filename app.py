import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Sprint Dashboard Viewer", layout="wide", page_icon="📊")

# Função para limpar e processar os dados
def process_data(df):
    # Remover colunas inúteis se existirem
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # Limpar dados marcados com '*'
    df = df.replace({'\*': None}, regex=True)
    
    # Converter datas
    date_cols = ['Criado', 'Start date', 'Início dos testes', 'Resolvido']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Mapeamento de Status
    status_map = {
        'Concluído': 'Done', 'Itens concluídos': 'Done',
        'Parking Lot': 'Backlog', 'Bloqueado': 'Blocked', 'EM APROVAÇÃO': 'In Progress',
        'Em Análise': 'In Progress', 'Pronta para publicação': 'Done',
        'Descartado': 'Cancelled', 'cancelado': 'Cancelled'
    }
    df['Status_Clean'] = df['Status'].map(status_map).fillna(df['Status'])

    # Se não tiver Story Points, criar uma métrica de contagem
    if 'Estimativa Tech Assessment' in df.columns:
        df['Story_Points'] = pd.to_numeric(df['Estimativa Tech Assessment'], errors='coerce').fillna(1)
    else:
        df['Story_Points'] = 1

    # Esforço (Adaptação caso não tenha as colunas no Excel)
    if 'Esforco_Dev' not in df.columns:
        df['Esforco_Dev'] = df['Story_Points'] * 1.5
        df['Esforco_QA'] = df['Story_Points'] * 0.5

    return df

# Interface de Upload
st.title("📊 SprintMind Dashboard Viewer")
st.markdown("Faça o upload do seu arquivo Excel exportado do Jira para visualizar as métricas da Sprint.")

uploaded_file = st.file_uploader("Escolha o arquivo Excel", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        df_raw = pd.read_excel(uploaded_file, engine='openpyxl')
        df = process_data(df_raw)
        
        # Filtros na Sidebar
        st.sidebar.header("Filtros")
        clientes = df['Cliente'].dropna().unique().tolist()
        selected_cliente = st.sidebar.multiselect("Selecione o Cliente", clientes, default=clientes)
        
        tipos = df['Tipo de item'].dropna().unique().tolist()
        selected_tipos = st.sidebar.multiselect("Tipo de Item", tipos, default=tipos)

        # Aplicar Filtros
        df_filtered = df[df['Cliente'].isin(selected_cliente) & df['Tipo de item'].isin(selected_tipos)]

        # KPIs Principais
        st.markdown("### Indicadores Principais")
        col1, col2, col3, col4 = st.columns(4)
        
        total_scope = df_filtered['Story_Points'].sum()
        done_items = df_filtered[df_filtered['Status_Clean'] == 'Done']
        completed_scope = done_items['Story_Points'].sum()
        progress_pct = (completed_scope / total_scope * 100) if total_scope > 0 else 0
        total_bugs = len(df_filtered[df_filtered['Tipo de item'] == 'Bug'])

        col1.metric("TOTAL SP (Escopo)", f"{total_scope:.0f}")
        col2.metric("SP ENTREGUES", f"{completed_scope:.0f}")
        col3.metric("PROGRESSO", f"{progress_pct:.1f}%")
        col4.metric("TOTAL DE BUGS", f"{total_bugs}")

        st.markdown("---")

        # Gráficos
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### Mix de Atividades (Geral)")
            mix_df = df_filtered.groupby('Tipo de item')['Story_Points'].sum().reset_index()
            fig_mix = px.pie(mix_df, values='Story_Points', names='Tipo de item', hole=0.5,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_mix.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True)
            st.plotly_chart(fig_mix, use_container_width=True)

        with col_chart2:
            st.markdown("#### Análise de Granularidade (Core)")
            gran_df = df_filtered[df_filtered['Story_Points'] > 0]
            if not gran_df.empty:
                fig_gran = px.histogram(gran_df, x="Story_Points", nbins=10, 
                                       title="Distribuição de Tamanho dos Cards (SP)",
                                       color_discrete_sequence=['#00b4d8'])
                fig_gran.update_layout(xaxis_title="Story Points", yaxis_title="Quantidade de Cards", bargap=0.2)
                st.plotly_chart(fig_gran, use_container_width=True)

        col_chart3, col_chart4 = st.columns(2)

        with col_chart3:
            st.markdown("#### Balanço: Esforço Dev vs QA")
            effort_df = df_filtered.agg({'Esforco_Dev': 'sum', 'Esforco_QA': 'sum'}).reset_index()
            effort_df.columns = ['Tipo', 'Esforço']
            fig_effort = px.bar(effort_df, x='Tipo', y='Esforço', color='Tipo', 
                                color_discrete_map={'Esforco_Dev': '#4361ee', 'Esforco_QA': '#f72585'})
            st.plotly_chart(fig_effort, use_container_width=True)

        with col_chart4:
            st.markdown("#### Status das Entregas")
            status_df = df_filtered.groupby('Status_Clean')['Story_Points'].sum().reset_index()
            fig_status = px.bar(status_df, x='Status_Clean', y='Story_Points', color='Status_Clean',
                               color_discrete_sequence=px.colors.qualitative.Vivid)
            fig_status.update_layout(xaxis_title="Status", yaxis_title="Story Points", showlegend=False)
            st.plotly_chart(fig_status, use_container_width=True)

        with st.expander("Ver Tabela de Dados Processada"):
            st.dataframe(df_filtered)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Aguardando o upload do arquivo Excel...")

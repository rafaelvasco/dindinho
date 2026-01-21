"""Category breakdown chart components."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from typing import Optional


def show_category_breakdown(api, start_date: Optional[date] = None, end_date: Optional[date] = None, category: Optional[str] = None, transaction_type: Optional[str] = None, title: str = "Transações por Categoria"):
    """Exibe gráfico de pizza de transações por categoria."""
    try:
        data = api.get_transactions_by_category(start_date=start_date, end_date=end_date, category=category, transaction_type=transaction_type)

        if not data["categories"]:
            st.info("Nenhum dado disponível para o período selecionado.")
            return

        # Create pie chart
        categories = [cat["category"] for cat in data["categories"]]
        totals = [cat["total"] for cat in data["categories"]]

        fig = px.pie(
            values=totals,
            names=categories,
            title=title,
            hole=0.3
        )

        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=True)

        st.plotly_chart(fig, use_container_width=True)

        # Show table
        with st.expander("📊 Ver Detalhes"):
            for cat in data["categories"]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{cat['category']}**")
                with col2:
                    st.markdown(f"R$ {cat['total']:,.2f}")

    except Exception as e:
        st.error(f"Erro ao carregar dados de categoria: {str(e)}")

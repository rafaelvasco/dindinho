"""Top transactions display components."""

import streamlit as st
from datetime import date
from typing import Optional


def show_top_transactions(api, start_date: Optional[date] = None, end_date: Optional[date] = None, category: Optional[str] = None, limit: int = 10, transaction_type: Optional[str] = None, title: Optional[str] = None):
    """Display top N biggest transactions."""
    if title is None:
        title = f"### 🏆 {limit} Maiores Transações"

    st.markdown(title)

    try:
        data = api.get_biggest_transactions(limit=limit, start_date=start_date, end_date=end_date, category=category, transaction_type=transaction_type)

        if not data["transactions"]:
            st.info("Nenhuma transação encontrada.")
            return

        for idx, transaction in enumerate(data["transactions"], 1):
            col1, col2, col3, col4 = st.columns([1, 3, 2, 1])

            with col1:
                st.markdown(f"**#{idx}**")

            with col2:
                st.markdown(f"**{transaction['description']}**")
                st.caption(f"{transaction['date']}")

            with col3:
                st.markdown(f"**R$ {transaction['amount']:,.2f}**")
                st.caption(transaction['category'])

            with col4:
                if transaction.get("transaction_type"):
                    st.caption(transaction["transaction_type"])

            if idx < len(data["transactions"]):
                st.markdown("---")

    except Exception as e:
        st.error(f"Error loading top transactions: {str(e)}")


def show_biggest_by_category(api, start_date: Optional[date] = None, end_date: Optional[date] = None, category: Optional[str] = None):
    """Display biggest transaction for each category."""
    st.markdown("### 🏆 Maiores Transações por Categoria")

    try:
        data = api.get_biggest_by_category(start_date=start_date, end_date=end_date, category=category)

        if not data["categories"]:
            st.info("Nenhuma transação encontrada.")
            return

        for cat_data in data["categories"]:
            transaction = cat_data["transaction"]

            with st.container():
                col1, col2, col3 = st.columns([2, 3, 2])

                with col1:
                    st.markdown(f"**{cat_data['category']}**")

                with col2:
                    st.markdown(f"**{transaction['description']}**")
                    st.caption(f"{transaction['date']}")

                with col3:
                    st.markdown(f"**R$ {transaction['amount']:,.2f}**")

                st.markdown("---")

    except Exception as e:
        st.error(f"Error loading biggest by category: {str(e)}")

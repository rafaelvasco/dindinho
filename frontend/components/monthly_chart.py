"""Monthly transaction chart components."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime


def show_monthly_chart(api, year: int):
    """Display bar chart of transactions by month."""
    try:
        data = api.get_transactions_by_month(year=year)

        if not data["months"]:
            st.info(f"Sem dados disponíveis para {year}.")
            return

        # Create bar chart
        months = []
        totals = []
        for month in data["months"]:
            # Format month as "Mon/Year" (e.g., "Jan/2024")
            # Parse YYYY-MM format by adding day component
            date_obj = datetime.strptime(month["month"], '%Y-%m')
            months.append(date_obj.strftime('%b/%Y'))
            totals.append(month["total"])

        fig = px.bar(
            x=months,
            y=totals,
            title=f"Monthly Transactions - {year}",
            labels={"x": "Month", "y": "Amount (R$)"}
        )

        fig.update_layout(showlegend=False)

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading monthly data: {str(e)}")


def show_monthly_comparison(api, year: int):
    """Display monthly comparison with change percentages."""
    try:
        data = api.get_monthly_comparison(year=year)

        if not data["months"]:
            st.info(f"Sem dados disponíveis para {year}.")
            return

        # Create line chart with change
        months = []
        totals = []
        changes = []

        for month_data in data["months"]:
            # Format month as "Mon/Year" (e.g., "Jan/2024")
            # Parse YYYY-MM format
            date_obj = datetime.strptime(month_data["month"], '%Y-%m')
            months.append(date_obj.strftime('%b/%Y'))
            totals.append(month_data["total"])
            changes.append(month_data.get("change_percent", 0))

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=months,
            y=totals,
            mode='lines+markers',
            name='Total',
            line=dict(width=3)
        ))

        fig.update_layout(
            title=f"Monthly Comparison - {year}",
            xaxis_title="Month",
            yaxis_title="Amount (R$)",
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

        # Show comparison table
        with st.expander("📊 View Details"):
            for month_data in data["months"]:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"**{month_data['month']}**")
                with col2:
                    st.markdown(f"R$ {month_data['total']:,.2f}")
                with col3:
                    st.markdown(f"{month_data['count']} transactions")
                with col4:
                    change = month_data.get("change_percent")
                    if change is not None:
                        color = "🔴" if change > 0 else "🟢"
                        st.markdown(f"{color} {change:+.1f}%")
                    else:
                        st.markdown("-")

    except Exception as e:
        st.error(f"Error loading comparison data: {str(e)}")

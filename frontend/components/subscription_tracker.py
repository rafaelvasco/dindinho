"""Subscription tracker component."""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from frontend.utils.confirmation import ConfirmationDialog


def show_subscription_tracker(api):
    """Display subscription tracker with historical values."""
    try:
        subscriptions_data = api.get_subscription_summary()

        if not subscriptions_data:
            st.info("Nenhuma assinatura encontrada. Marque transações como assinaturas ao importar para que elas apareçam aqui.")
            return

        # Summary metrics
        active_subs = [s for s in subscriptions_data if s["is_active"]]
        total_monthly = sum(s["current_value"] for s in active_subs)

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Active Subscriptions", len(active_subs))

        with col2:
            st.metric("Total Monthly Cost", f"R$ {total_monthly:,.2f}")

        st.markdown("---")

        # List subscriptions
        for sub in subscriptions_data:
            with st.expander(f"{'✅' if sub['is_active'] else '❌'} {sub['name']} - R$ {sub['current_value']:,.2f}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown(f"**Current Value:** R$ {sub['current_value']:,.2f}")
                    st.markdown(f"**Average:** R$ {sub['average_value']:,.2f}")

                with col2:
                    st.markdown(f"**Transactions:** {sub['transaction_count']}")
                    st.markdown(f"**Status:** {'Active' if sub['is_active'] else 'Inactive'}")

                with col3:
                    if sub['first_date']:
                        # Handle both YYYY-MM and YYYY-MM-DD formats
                        date_str = sub['first_date'][:7]  # Take only YYYY-MM part
                        first_date = datetime.strptime(date_str, '%Y-%m').strftime('%b/%Y')
                        st.markdown(f"**First:** {first_date}")
                    if sub['last_date']:
                        # Handle both YYYY-MM and YYYY-MM-DD formats
                        date_str = sub['last_date'][:7]  # Take only YYYY-MM part
                        last_date = datetime.strptime(date_str, '%Y-%m').strftime('%b/%Y')
                        st.markdown(f"**Last:** {last_date}")

                # Historical chart
                if sub["historical_values"]:
                    dates = []
                    amounts = []

                    for h in sub["historical_values"]:
                        # Format date as "Mon/Year" (e.g., "Jan/2024")
                        # Handle both YYYY-MM and YYYY-MM-DD formats
                        date_str = h["date"][:7]  # Take only YYYY-MM part
                        date_obj = datetime.strptime(date_str, '%Y-%m')
                        dates.append(date_obj.strftime('%b/%Y'))
                        amounts.append(h["amount"])

                    fig = go.Figure()

                    # Use bar chart for better visibility with few data points
                    fig.add_trace(go.Bar(
                        x=dates,
                        y=amounts,
                        name=sub['name'],
                        marker=dict(color='#1f77b4')
                    ))

                    fig.update_layout(
                        title=f"{sub['name']} - Historical Values",
                        xaxis_title="Month",
                        yaxis_title="Amount (R$)",
                        height=300,
                        showlegend=False
                    )

                    st.plotly_chart(fig, use_container_width=True)

                # Actions
                col1, col2 = st.columns(2)

                with col1:
                    if st.button(f"{'Deactivate' if sub['is_active'] else 'Activate'}", key=f"toggle_{sub['id']}"):
                        try:
                            api.update_subscription(sub['id'], {"is_active": not sub['is_active']})
                            st.success("Updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                with col2:
                    if st.button("Delete", key=f"delete_{sub['id']}", type="secondary"):
                        def delete_subscription():
                            try:
                                api.delete_subscription(sub['id'])
                                st.success("Subscription deleted!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                        ConfirmationDialog.show_delete_confirmation(
                            item_name=f"'{sub['name']}'",
                            on_confirm=delete_subscription,
                            title="Delete Subscription",
                            message=f"⚠️ This will permanently delete **{sub['name']}** and all its historical data.",
                            confirm_label="Yes, delete permanently",
                            cancel_label="Cancel"
                        )

    except Exception as e:
        st.error(f"Error loading subscriptions: {str(e)}")

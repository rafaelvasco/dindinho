"""Main Streamlit application for Finance Analysis."""

import streamlit as st
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from frontend.utils.api_client import get_api_client
from frontend.components.month_selector import render_month_selector
from frontend.components.category_pills import render_category_pills

# Page config
st.set_page_config(
    page_title="Dindinho",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-message {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-message {
        padding: 1rem;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize API client
api = get_api_client()

# Sidebar
with st.sidebar:
    st.markdown("### 💰 Dindinho Finanças")
    st.markdown("---")

    # Check API health
    try:
        health = api.health_check()
        st.success("✅ Online")
    except Exception as e:
        st.error(f"❌ Offline: {str(e)}")
        st.stop()

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 1rem; color: #666;'>
        <small>Dindinho v0.1.0</small><br>
        <small>Powered by Claude AI</small>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-header">Dindinho Finanças</div>', unsafe_allow_html=True)

# Define tabs
TAB_LABELS = [
    "📊 Dashboard",
    "📤 Importar CSV",
    "💳 Transações",
    "🔄 Assinaturas",
    "💰 Fontes de Dinheiro",
    "📈 Relatórios",
    "🏷️ Categorias",
    "⚙️ Configurações"
]

# Initialize tab selection in session state FIRST (before any components that might rerun)
if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = 0

# Create tab navigation using radio buttons (preserves state across reruns)
selected_tab = st.radio(
    "Navegação",
    options=range(len(TAB_LABELS)),
    format_func=lambda x: TAB_LABELS[x],
    key="selected_tab",
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

# Render month/year selector only for tabs that need it (not Reports)
if selected_tab not in [5]:  # Tab 5 is Reports
    start_date, end_date = render_month_selector()
    st.markdown("---")

# Tab 0: Overview Dashboard
if selected_tab == 0:
    # Import components
    from frontend.components.category_chart import show_category_breakdown
    from frontend.components.monthly_chart import show_monthly_chart
    from frontend.components.top_transactions import show_top_transactions

    # EXPECTED INCOME Section
    st.markdown("## 💸 RECEITAS ESPERADAS")
    st.markdown("---")

    try:
        expected_data = api.get_expected_income_summary(
            year=start_date.year,
            month=start_date.month
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Receitas Esperadas",
                f"R$ {expected_data['expected_total']:,.2f}",
                help="Total esperado de receitas neste mês"
            )

        with col2:
            st.metric(
                "Receitas Recebidas",
                f"R$ {expected_data['actual_total']:,.2f}",
                help="Total recebido até agora"
            )

        with col3:
            difference = expected_data['actual_total'] - expected_data['expected_total']
            st.metric(
                "Diferença",
                f"R$ {difference:,.2f}",
                delta=f"R$ {difference:,.2f}",
                delta_color="normal" if difference >= 0 else "inverse",
                help="Diferença entre esperado e recebido"
            )

        # Optional: Show per-source breakdown
        if expected_data.get('sources'):
            with st.expander("📋 Detalhamento por Fonte"):
                for source in expected_data['sources']:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{source['name']}**")
                    with col2:
                        st.write(f"Esperado: R$ {source['expected_amount']:,.2f}")
                    with col3:
                        st.write(f"Recebido: R$ {source['actual_amount']:,.2f}")

    except Exception as e:
        st.error(f"Erro ao carregar receitas esperadas: {str(e)}")

    st.markdown("---")
    st.markdown("")

    # INCOME Section
    st.markdown("## 💰 RECEITAS (Entradas)")
    st.markdown("---")

    # Show statistics for INCOME
    try:
        income_stats = api.get_statistics(start_date=start_date, end_date=end_date, transaction_type="INCOME")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Transações", income_stats["total_transactions"])

        with col2:
            st.metric("Valor Total", f"R$ {income_stats['total_amount']:,.2f}")

        with col3:
            st.metric("Média de Transações", f"R$ {income_stats['average_amount']:,.2f}")

        with col4:
            st.metric("Categorias", income_stats["category_count"])

    except Exception as e:
        st.error(f"Erro ao carregar estatísticas de receitas: {str(e)}")

    st.markdown("")

    # INCOME Charts and Top Transactions
    col1, col2 = st.columns(2)

    with col1:
        show_category_breakdown(api, start_date, end_date, transaction_type="INCOME", title="Receitas por Categoria")

    with col2:
        show_top_transactions(api, start_date, end_date, limit=10, transaction_type="INCOME", title="### 🏆 Top 10 Receitas")

    st.markdown("---")
    st.markdown("")

    # EXPENSE Section
    st.markdown("## 💳 DESPESAS (Saídas)")
    st.markdown("---")

    # Show statistics for EXPENSE
    try:
        expense_stats = api.get_statistics(start_date=start_date, end_date=end_date, transaction_type="EXPENSE")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Transações", expense_stats["total_transactions"])

        with col2:
            st.metric("Valor Total", f"R$ {expense_stats['total_amount']:,.2f}")

        with col3:
            st.metric("Média de Transações", f"R$ {expense_stats['average_amount']:,.2f}")

        with col4:
            st.metric("Categorias", expense_stats["category_count"])

    except Exception as e:
        st.error(f"Erro ao carregar estatísticas de despesas: {str(e)}")

    st.markdown("")

    # EXPENSE Charts and Top Transactions
    col1, col2 = st.columns(2)

    with col1:
        show_category_breakdown(api, start_date, end_date, transaction_type="EXPENSE", title="Despesas por Categoria")

    with col2:
        show_top_transactions(api, start_date, end_date, limit=10, transaction_type="EXPENSE", title="### 🏆 Top 10 Despesas")

    st.markdown("---")
    st.markdown("")

    # PAYMENT Section
    st.markdown("## 💸 PAGAMENTOS (Transferências/Cartões)")
    st.markdown("---")

    # Show statistics for PAYMENT
    try:
        payment_stats = api.get_statistics(start_date=start_date, end_date=end_date, transaction_type="PAYMENT")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Transações", payment_stats["total_transactions"])

        with col2:
            st.metric("Valor Total", f"R$ {payment_stats['total_amount']:,.2f}")

        with col3:
            st.metric("Média de Transações", f"R$ {payment_stats['average_amount']:,.2f}")

        with col4:
            st.metric("Categorias", payment_stats["category_count"])

    except Exception as e:
        st.error(f"Erro ao carregar estatísticas de pagamentos: {str(e)}")

    st.markdown("")

    # PAYMENT Charts and Top Transactions
    col1, col2 = st.columns(2)

    with col1:
        show_category_breakdown(api, start_date, end_date, transaction_type="PAYMENT", title="Pagamentos por Categoria")

    with col2:
        show_top_transactions(api, start_date, end_date, limit=10, transaction_type="PAYMENT", title="### 🏆 Top 10 Pagamentos")

# Tab 1: Import CSV
elif selected_tab == 1:
    from frontend.components.import_dialog import show_import_dialog

    show_import_dialog(api)

# Tab 2: Transactions
elif selected_tab == 2:
    from frontend.components.transaction_table import show_transaction_table
    from frontend.components.category_pills import render_category_pills

    # Render category filter only for transactions tab
    selected_category = render_category_pills()

    show_transaction_table(api, start_date, end_date, selected_category)

# Tab 3: Subscriptions
elif selected_tab == 3:
    from frontend.components.subscription_tracker import show_subscription_tracker

    show_subscription_tracker(api)

# Tab 4: Income Sources (Fontes de Dinheiro)
elif selected_tab == 4:
    from frontend.components.income_source_manager import show_income_source_manager

    show_income_source_manager(api)

# Tab 5: Reports
elif selected_tab == 5:
    from datetime import date as Date
    from dateutil.relativedelta import relativedelta

    st.markdown("## 📈 Relatório Anual - Year to Date")

    # Year selector
    current_year_now = datetime.now().year
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        selected_year = st.selectbox(
            "Selecione o Ano",
            options=list(range(2020, current_year_now + 1)),
            index=list(range(2020, current_year_now + 1)).index(current_year_now),
            key="year_selector"
        )

    st.markdown(f"### Resumo Mensal - {selected_year}")
    st.markdown("---")

    # Get current year and month (for limiting months shown)
    current_year = selected_year
    # If selected year is current year, only show up to current month
    # Otherwise show all 12 months
    if selected_year == current_year_now:
        current_month = datetime.now().month
    else:
        current_month = 12

    # Month names in Portuguese
    month_names = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    # Loop through each month from January to current month
    for month_num in range(1, current_month + 1):
        # Calculate date range for this month
        month_start = Date(current_year, month_num, 1)
        if month_num == 12:
            month_end = Date(current_year, 12, 31)
        else:
            month_end = Date(current_year, month_num + 1, 1) - relativedelta(days=1)

        month_name = month_names[month_num]

        # Expandable section for each month
        with st.expander(f"📅 {month_name} {current_year}", expanded=(month_num == current_month)):
            try:
                # Get statistics for each transaction type
                expense_stats = api.get_statistics(
                    start_date=month_start,
                    end_date=month_end,
                    transaction_type="EXPENSE"
                )

                payment_stats = api.get_statistics(
                    start_date=month_start,
                    end_date=month_end,
                    transaction_type="PAYMENT"
                )

                income_stats = api.get_statistics(
                    start_date=month_start,
                    end_date=month_end,
                    transaction_type="INCOME"
                )

                # Calculate totals
                total_spent = expense_stats.get('total_amount', 0) + payment_stats.get('total_amount', 0)
                total_earned = income_stats.get('total_amount', 0)
                net_balance = total_earned - total_spent

                # Display summary metrics
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "💸 Total Gasto",
                        f"R$ {total_spent:,.2f}",
                        help="Despesas + Pagamentos"
                    )

                with col2:
                    st.metric(
                        "💰 Total Recebido",
                        f"R$ {total_earned:,.2f}",
                        help="Receitas"
                    )

                with col3:
                    st.metric(
                        "📊 Saldo Líquido",
                        f"R$ {net_balance:,.2f}",
                        delta=f"R$ {net_balance:,.2f}",
                        delta_color="normal" if net_balance >= 0 else "inverse"
                    )

                st.markdown("---")

                # Category breakdowns
                col_left, col_right = st.columns(2)

                with col_left:
                    st.markdown("#### 💳 Gastos por Categoria")

                    # Get category breakdown for expenses
                    expense_categories = api.get_transactions_by_category(
                        start_date=month_start,
                        end_date=month_end,
                        transaction_type="EXPENSE"
                    )

                    # Get category breakdown for payments
                    payment_categories = api.get_transactions_by_category(
                        start_date=month_start,
                        end_date=month_end,
                        transaction_type="PAYMENT"
                    )

                    # Combine expenses and payments
                    all_spending = {}
                    for cat in expense_categories.get('categories', []):
                        all_spending[cat['category']] = cat['total']
                    for cat in payment_categories.get('categories', []):
                        if cat['category'] in all_spending:
                            all_spending[cat['category']] += cat['total']
                        else:
                            all_spending[cat['category']] = cat['total']

                    # Sort by amount (descending)
                    sorted_spending = sorted(all_spending.items(), key=lambda x: x[1], reverse=True)

                    if sorted_spending:
                        for category, amount in sorted_spending:
                            percentage = (amount / total_spent * 100) if total_spent > 0 else 0
                            st.write(f"**{category}**: R$ {amount:,.2f} ({percentage:.1f}%)")
                    else:
                        st.info("Nenhum gasto neste mês")

                with col_right:
                    st.markdown("#### 💰 Receitas por Categoria")

                    # Get category breakdown for income
                    income_categories = api.get_transactions_by_category(
                        start_date=month_start,
                        end_date=month_end,
                        transaction_type="INCOME"
                    )

                    # Sort by amount (descending)
                    sorted_income = sorted(
                        income_categories.get('categories', []),
                        key=lambda x: x['total'],
                        reverse=True
                    )

                    if sorted_income:
                        for cat in sorted_income:
                            percentage = (cat['total'] / total_earned * 100) if total_earned > 0 else 0
                            st.write(f"**{cat['category']}**: R$ {cat['total']:,.2f} ({percentage:.1f}%)")
                    else:
                        st.info("Nenhuma receita neste mês")

            except Exception as e:
                st.error(f"Erro ao carregar dados de {month_name}: {str(e)}")

# Tab 6: Categories
elif selected_tab == 6:
    from frontend.components.category_manager import show_category_manager

    show_category_manager(api)

# Tab 7: Settings
elif selected_tab == 7:
    from frontend.components.ignore_list_manager import show_ignore_list_manager

    st.markdown("### 🚫 Ignore List Management")
    st.info("Transações com esses nomes/descrições serão automaticamente ignoradas durante a importação.")

    show_ignore_list_manager(api)

    st.markdown("---")
    st.markdown("### 🔧 Dados da Aplicação:")

    try:
        health = api.health_check()
        st.json(health)
    except Exception as e:
        st.error(f"Não foi possível conectar ao backend: {str(e)}")

"""Transaction table component for viewing and managing transactions."""

import streamlit as st
import pandas as pd
from datetime import date
from typing import Optional
from frontend.utils.confirmation import ConfirmationDialog


def show_transaction_table(api, start_date: date, end_date: date, category: Optional[str] = None):
    """
    Display transaction table with filters and actions.

    Args:
        api: API client instance
        start_date: Start date filter
        end_date: End date filter
        category: Category filter (optional)
    """
    # Manual transaction creation form
    with st.expander("➕ Criar Transação Manualmente", expanded=False):
        st.info("💡 Use este formulário para adicionar transações que não vieram de importação CSV (ex: receitas de fontes específicas)")

        with st.form("create_transaction_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                txn_date = st.date_input(
                    "Data*",
                    value=date.today(),
                    help="Data da transação"
                )

                description = st.text_input(
                    "Descrição*",
                    placeholder="Ex: Salário Empresa X - Janeiro/2024",
                    help="Descrição da transação"
                )

                amount = st.number_input(
                    "Valor*",
                    min_value=0.0,
                    step=100.0,
                    format="%.2f",
                    help="Valor da transação (sempre positivo)"
                )

            with col2:
                txn_type = st.selectbox(
                    "Tipo*",
                    options=["INCOME", "EXPENSE", "PAYMENT", "REFUND"],
                    format_func=lambda x: {
                        "INCOME": "💰 Receita",
                        "EXPENSE": "💸 Despesa",
                        "PAYMENT": "💳 Pagamento",
                        "REFUND": "🔙 Reembolso"
                    }[x],
                    help="Tipo de transação"
                )

                # Get categories for the dropdown
                try:
                    cat_data = api.get_transactions_by_category()
                    category_options = [cat["category"] for cat in cat_data["categories"]]
                except:
                    category_options = ["Outros"]

                category_select = st.selectbox(
                    "Categoria*",
                    options=category_options,
                    help="Categoria da transação"
                )

                source_type = st.selectbox(
                    "Origem*",
                    options=["manual", "account_extract", "credit_card"],
                    format_func=lambda x: {
                        "manual": "📝 Manual",
                        "account_extract": "🏦 Extrato Bancário",
                        "credit_card": "💳 Cartão de Crédito"
                    }[x],
                    help="Origem da transação"
                )

            submitted = st.form_submit_button("Criar Transação", type="primary", use_container_width=True)

            if submitted:
                if not description:
                    st.error("Descrição é obrigatória!")
                elif amount <= 0:
                    st.error("Valor deve ser maior que zero!")
                else:
                    try:
                        api.create_transaction({
                            "date": txn_date.isoformat(),
                            "description": description,
                            "amount": amount,
                            "currency": "BRL",
                            "transaction_type": txn_type,
                            "category": category_select,
                            "source_type": source_type,
                            "source_file": None,
                            "raw_data": None,
                            "original_category": None,
                            "subscription_id": None
                        })
                        st.success(f"✅ Transação '{description}' criada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar transação: {str(e)}")

    st.markdown("---")

    # Search box
    search = st.text_input("🔍 Buscar transações", placeholder="Buscar por descrição...")

    try:
        # Fetch transactions
        response = api.get_transactions(
            start_date=start_date,
            end_date=end_date,
            category=category,
            search=search if search else None,
            limit=100
        )

        transactions = response["transactions"]
        total = response["total"]

        if not transactions:
            st.info("Sem transações encontradas para os filtros selecionados")
            return

        # Get available categories for editing
        try:
            cat_data = api.get_transactions_by_category()
            categories = [cat["category"] for cat in cat_data["categories"]]
        except:
            categories = []

        # Get available income sources for editing
        income_sources_dict = {"(Nenhuma)": None}  # Default option
        try:
            income_sources_response = api.get_income_sources(active_only=False)
            income_sources = income_sources_response.get("income_sources", [])
            for source in income_sources:
                income_sources_dict[source["name"]] = source["id"]
        except:
            pass

        # Create reverse mapping (id -> name) for display
        id_to_name = {v: k for k, v in income_sources_dict.items()}

        # Summary
        st.markdown(f"**Mostrando {len(transactions)} de {total} transações**")

        # Convert to DataFrame with editable columns
        df = pd.DataFrame([
            {
                "Excluir": False,
                "ID": txn["id"],
                "Data": txn["date"],
                "Descrição": txn["description"],
                "Valor": f"R$ {txn['amount']:,.2f}",
                "Categoria": txn["category"],
                "Tipo": txn.get("transaction_type", "-"),
                "Fonte de Renda": id_to_name.get(txn.get("income_source_id"), "(Nenhuma)") if txn.get("transaction_type") == "INCOME" else "-",
                "Origem": txn["source_type"],
            }
            for txn in transactions
        ])

        # Display editable table
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=["ID", "Data", "Valor", "Tipo", "Origem"],
            column_config={
                "Excluir": st.column_config.CheckboxColumn(
                    "Excluir",
                    help="Marcar para excluir",
                    default=False,
                ),
                "Categoria": st.column_config.SelectboxColumn(
                    "Categoria",
                    options=categories,
                    required=True,
                ),
                "Descrição": st.column_config.TextColumn(
                    "Descrição",
                    max_chars=200,
                ),
                "Fonte de Renda": st.column_config.SelectboxColumn(
                    "Fonte de Renda",
                    options=list(income_sources_dict.keys()),
                    help="Vincular receita a uma fonte (somente para transações INCOME)",
                ),
            }
        )

        # Process changes
        if not edited_df.equals(df):
            # Check for edited rows
            for idx, (original_row, edited_row) in enumerate(zip(df.itertuples(), edited_df.itertuples())):
                transaction_id = edited_row.ID
                transaction_type = edited_row.Tipo
                updates = {}

                # Check if category changed
                if edited_row.Categoria != original_row.Categoria:
                    updates["category"] = edited_row.Categoria

                # Check if description changed
                if edited_row.Descrição != original_row.Descrição:
                    updates["description"] = edited_row.Descrição

                # Check if income source changed (only for INCOME transactions)
                if hasattr(edited_row, '_8'):  # "Fonte de Renda" is 8th column (0-indexed: column 7)
                    fonte_atual = getattr(edited_row, '_8', None)
                    fonte_original = getattr(original_row, '_8', None)

                    if fonte_atual != fonte_original and transaction_type == "INCOME":
                        # Map name back to ID
                        new_source_id = income_sources_dict.get(fonte_atual)
                        updates["income_source_id"] = new_source_id if new_source_id is not None else 0  # 0 means unlink

                # Apply updates if any
                if updates:
                    try:
                        api.update_transaction(transaction_id, updates)
                        st.success(f"✅ Transação {transaction_id} atualizada")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar transação {transaction_id}: {str(e)}")
                        break

        # Handle deletions
        rows_to_delete = edited_df[edited_df["Excluir"] == True]
        if not rows_to_delete.empty:
            transaction_count = len(rows_to_delete)
            if st.button(f"🗑️ Excluir {transaction_count} transação(ões) selecionada(s)", type="primary"):
                def delete_transactions():
                    deleted_count = 0
                    errors = []

                    for _, row in rows_to_delete.iterrows():
                        try:
                            api.delete_transaction(row["ID"])
                            deleted_count += 1
                        except Exception as e:
                            errors.append(f"ID {row['ID']}: {str(e)}")

                    if deleted_count > 0:
                        st.success(f"✅ {deleted_count} transação(ões) excluída(s)")
                    if errors:
                        st.error(f"Erros ao excluir: {'; '.join(errors)}")

                    st.rerun()

                ConfirmationDialog.show_delete_confirmation(
                    item_name=f"{transaction_count} transaction(s)",
                    on_confirm=delete_transactions,
                    title="Delete Transactions",
                    message=f"⚠️ You are about to delete **{transaction_count}** transaction(s).",
                    confirm_label=f"Delete {transaction_count} transaction(s)",
                    cancel_label="Cancel"
                )

    except Exception as e:
        st.error(f"Erro ao carregar transações: {str(e)}")

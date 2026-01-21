"""Income source manager component."""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import re


def format_cnpj(cnpj: str) -> str:
    """Format CNPJ for display (XX.XXX.XXX/XXXX-XX)."""
    if not cnpj or len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"


def validate_cnpj(cnpj: str) -> bool:
    """Validate CNPJ format."""
    if not cnpj:
        return True  # Optional field
    # Remove formatting
    digits = re.sub(r"[^\d]", "", cnpj)
    return len(digits) == 14


@st.dialog("Confirmar Exclusão")
def confirm_delete(api, source_id, source_name):
    """Confirmation dialog for deleting income source."""
    st.warning(f"⚠️ Tem certeza que deseja excluir **{source_name}**?")
    st.markdown("Esta ação irá desvincular todas as transações associadas, mas não as excluirá.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirmar", type="primary", use_container_width=True):
            try:
                api.delete_income_source(source_id)
                st.success("Fonte de dinheiro excluída com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {str(e)}")
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()


def show_income_source_manager(api):
    """Display income source manager with CRUD operations."""
    st.markdown("## 💰 Gerenciamento de Fontes de Dinheiro")

    try:
        # Fetch income sources
        response = api.get_income_sources(active_only=False)
        income_sources = response.get("income_sources", [])

        # Summary metrics
        active_sources = [s for s in income_sources if s["is_active"]]
        total_expected = sum(s["current_expected_amount"] for s in active_sources)

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Fontes Ativas", len(active_sources))

        with col2:
            st.metric("Receita Mensal Esperada", f"R$ {total_expected:,.2f}")

        st.markdown("---")

        # Create new income source form
        with st.expander("➕ Criar Nova Fonte de Dinheiro", expanded=False):
            with st.form("create_income_source_form", clear_on_submit=True):
                name = st.text_input(
                    "Nome*",
                    placeholder="Ex: Salário Empresa X",
                    help="Nome identificador da fonte de dinheiro"
                )

                cnpj = st.text_input(
                    "CNPJ (opcional)",
                    placeholder="XX.XXX.XXX/XXXX-XX",
                    help="CNPJ da empresa pagadora (14 dígitos)"
                )

                description = st.text_area(
                    "Descrição (opcional)",
                    placeholder="Ex: Salário mensal, pagamento dia 5",
                    help="Detalhes adicionais sobre esta fonte de renda"
                )

                expected_amount = st.number_input(
                    "Valor Mensal Esperado*",
                    min_value=0.0,
                    step=100.0,
                    format="%.2f",
                    help="Quanto você espera receber mensalmente desta fonte"
                )

                submitted = st.form_submit_button("Criar Fonte de Dinheiro", type="primary", use_container_width=True)

                if submitted:
                    if not name:
                        st.error("Nome é obrigatório!")
                    elif expected_amount <= 0:
                        st.error("Valor esperado deve ser maior que zero!")
                    elif cnpj and not validate_cnpj(cnpj):
                        st.error("CNPJ inválido! Deve ter 14 dígitos.")
                    else:
                        try:
                            # Clean CNPJ
                            cnpj_digits = re.sub(r"[^\d]", "", cnpj) if cnpj else None

                            api.create_income_source({
                                "name": name,
                                "cnpj": cnpj_digits,
                                "description": description,
                                "initial_expected_amount": expected_amount
                            })
                            st.success(f"✅ Fonte de dinheiro '{name}' criada com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao criar: {str(e)}")

        st.markdown("---")

        # List income sources
        if not income_sources:
            st.info("📭 Nenhuma fonte de dinheiro cadastrada. Crie uma acima para começar!")
            return

        st.markdown("### Suas Fontes de Dinheiro")

        for source in income_sources:
            status_icon = "✅" if source['is_active'] else "❌"
            with st.expander(
                f"{status_icon} {source['name']} - R$ {source['current_expected_amount']:,.2f}",
                expanded=False
            ):
                # Source details
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown(f"**Valor Esperado:** R$ {source['current_expected_amount']:,.2f}")
                    if source.get('cnpj'):
                        st.markdown(f"**CNPJ:** {format_cnpj(source['cnpj'])}")

                with col2:
                    st.markdown(f"**Status:** {'Ativo' if source['is_active'] else 'Inativo'}")
                    if source.get('description'):
                        st.markdown(f"**Descrição:** {source['description']}")

                with col3:
                    st.markdown(f"**Criado em:** {datetime.fromisoformat(source['created_at']).strftime('%d/%m/%Y')}")

                st.markdown("---")

                # Update expected amount form
                with st.expander("✏️ Atualizar Valor Esperado"):
                    with st.form(f"update_amount_form_{source['id']}"):
                        new_amount = st.number_input(
                            "Novo Valor Mensal Esperado",
                            min_value=0.0,
                            value=float(source['current_expected_amount']),
                            step=100.0,
                            format="%.2f",
                            key=f"amount_{source['id']}"
                        )

                        note = st.text_area(
                            "Motivo da alteração (opcional)",
                            placeholder="Ex: Aumento salarial, mudança de contrato",
                            key=f"note_{source['id']}"
                        )

                        if st.form_submit_button("Atualizar Valor", type="primary"):
                            try:
                                api.update_expected_amount(
                                    source['id'],
                                    new_amount,
                                    note if note else None
                                )
                                st.success("✅ Valor esperado atualizado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar: {str(e)}")

                # Historical chart
                if source.get("historical_values"):
                    st.markdown("**📈 Histórico de Valores Esperados**")

                    dates = []
                    amounts = []
                    notes = []

                    for h in source["historical_values"]:
                        # Format date
                        date_str = h["date"][:10]  # YYYY-MM-DD
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        dates.append(date_obj.strftime('%d/%m/%Y'))
                        amounts.append(h["amount"])
                        notes.append(h.get("note", ""))

                    # Reverse to show oldest first
                    dates.reverse()
                    amounts.reverse()
                    notes.reverse()

                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=amounts,
                        mode='lines+markers',
                        name='Valor Esperado',
                        marker=dict(color='#2ecc71', size=8),
                        line=dict(color='#2ecc71', width=2),
                        hovertemplate='<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>'
                    ))

                    fig.update_layout(
                        xaxis_title="Data",
                        yaxis_title="Valor Esperado (R$)",
                        height=300,
                        showlegend=False,
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Show notes if any
                    if any(notes):
                        with st.expander("📝 Ver Notas das Alterações"):
                            for i, (date, amount, note) in enumerate(zip(dates, amounts, notes)):
                                if note:
                                    st.markdown(f"**{date}** - R$ {amount:,.2f}")
                                    st.caption(f"_{note}_")
                                    if i < len(dates) - 1:
                                        st.markdown("---")

                # Actions
                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    toggle_label = "Desativar" if source['is_active'] else "Ativar"
                    if st.button(toggle_label, key=f"toggle_{source['id']}", use_container_width=True):
                        try:
                            api.update_income_source(
                                source['id'],
                                {"is_active": not source['is_active']}
                            )
                            st.success(f"✅ Fonte {'desativada' if source['is_active'] else 'ativada'}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {str(e)}")

                with col2:
                    if st.button("🗑️ Excluir", key=f"delete_{source['id']}", use_container_width=True):
                        confirm_delete(api, source['id'], source['name'])

    except Exception as e:
        st.error(f"Erro ao carregar fontes de dinheiro: {str(e)}")

"""Componente de gerenciamento de categorias para editar nomes de categorias."""

import streamlit as st
import pandas as pd


def show_category_manager(api):
    """
    Exibe interface de gerenciamento de categorias.

    Args:
        api: Instância do cliente API
    """
    st.markdown("### 🏷️ Gerenciamento de Categorias")
    st.info("Edite os nomes das categorias diretamente na tabela. As alterações afetarão todas as transações que usam esta categoria.")

    try:
        # Buscar todas as categorias
        categories = api.get_all_categories()

        if not categories:
            st.warning("Nenhuma categoria encontrada. Importe algumas transações para criar categorias.")
            return

        # Converter para DataFrame para melhor exibição
        df = pd.DataFrame(categories)
        df = df.rename(columns={
            "id": "ID",
            "name": "Nome",
            "created_at": "Criado em"
        })

        # Filtrar categorias especiais não editáveis (Assinaturas tem ID=1)
        editable_df = df[df["ID"] != 1].copy()

        if len(editable_df) == 0:
            st.warning("Nenhuma categoria editável disponível. Importe algumas transações para criar categorias.")
            return

        # Exibir tabela de categorias com edição inline
        st.markdown("#### Categorias Editáveis")

        # Usar data_editor para permitir edição inline
        edited_df = st.data_editor(
            editable_df[["ID", "Nome", "Criado em"]],
            use_container_width=True,
            hide_index=True,
            disabled=["ID", "Criado em"],  # Apenas "Nome" é editável
            key="category_editor"
        )

        # Detectar mudanças e atualizar categorias
        if edited_df is not None:
            for idx in range(len(editable_df)):
                original_name = editable_df.iloc[idx]["Nome"]
                edited_name = edited_df.iloc[idx]["Nome"]
                category_id = editable_df.iloc[idx]["ID"]

                if original_name != edited_name and edited_name.strip():
                    try:
                        api.update_category(category_id, {"name": edited_name.strip()})
                        st.success(f"✅ Categoria atualizada de '{original_name}' para '{edited_name.strip()}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar categoria: {str(e)}")
                        break

    except Exception as e:
        st.error(f"Erro ao carregar categorias: {str(e)}")

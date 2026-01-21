"""Componente de gerenciamento de lista de ignorados."""

import streamlit as st


def show_ignore_list_manager(api):
    """Exibe e gerencia a lista de ignorados."""
    try:
        ignore_list = api.get_ignore_list()

        if not ignore_list:
            st.info("Lista de ignorados vazia. Adicione descrições durante a importação de CSV ou manualmente abaixo.")
        else:
            st.markdown(f"**{len(ignore_list)} itens na lista de ignorados**")

            # Display ignore list
            for item in ignore_list:
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.markdown(f"🚫 {item['description']}")
                    st.caption(f"Adicionado: {item['created_at'][:10]}")

                with col2:
                    if st.button("Remover", key=f"remove_{item['id']}"):
                        try:
                            api.remove_from_ignore_list(item['id'])
                            st.success(f"Removido '{item['description']}'")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {str(e)}")

                st.markdown("---")

        # Add new item
        st.markdown("### Adicionar à Lista de Ignorados")

        with st.form("add_ignore"):
            description = st.text_input("Descrição da transação a ignorar")

            if st.form_submit_button("Adicionar à Lista"):
                if description:
                    try:
                        api.add_to_ignore_list(description)
                        st.success(f"✅ Adicionado '{description}' à lista de ignorados")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {str(e)}")
                else:
                    st.warning("Por favor, digite uma descrição")

    except Exception as e:
        st.error(f"Erro ao carregar lista de ignorados: {str(e)}")

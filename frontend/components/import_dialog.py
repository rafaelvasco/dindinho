"""CSV import dialog component with item marking functionality."""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List


def show_import_history(api):
    """Display the history of imported CSV files."""
    try:
        history = api.get_import_history()

        if not history:
            st.info("Nenhum arquivo CSV foi importado ainda.")
            return

        st.markdown("### Historico de Importacoes")

        # Create DataFrame for display
        df = pd.DataFrame(history)

        # Format the data for display
        df["source_type"] = df["source_type"].apply(
            lambda x: "Cartao de Credito" if x == "credit_card" else "Extrato Bancario"
        )

        # Format import_date
        df["import_date"] = pd.to_datetime(df["import_date"]).dt.strftime("%d/%m/%Y %H:%M")

        # Rename columns for display
        df = df.rename(columns={
            "source_file": "Arquivo",
            "source_type": "Tipo",
            "transaction_count": "Transacoes",
            "import_date": "Data de Importacao"
        })

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Arquivo": st.column_config.TextColumn("Arquivo", width="medium"),
                "Tipo": st.column_config.TextColumn("Tipo", width="small"),
                "Transacoes": st.column_config.NumberColumn("Transacoes", width="small"),
                "Data de Importacao": st.column_config.TextColumn("Data de Importacao", width="medium")
            }
        )

    except Exception as e:
        st.error(f"Erro ao carregar historico de importacoes: {str(e)}")


def show_import_dialog(api):
    """
    Display CSV import dialog with preview and item marking.

    Allows users to:
    - Upload CSV file
    - Preview parsed items
    - Mark items as: subscription, ignore once, ignore always
    - Confirm and import
    """
    st.markdown("### Passo 1: Enviar Arquivo CSV")

    # File uploader
    uploaded_file = st.file_uploader(
        "Escolha um arquivo CSV",
        type=["csv"],
        help="Upload credit card statement or account extract CSV"
    )

    if uploaded_file is not None:
        # Preview the file
        with st.expander("📄 Ver Conteúdo do Arquivo"):
            # Try encodings common for pt-BR files
            encodings = [
                ('utf-8', 'UTF-8'),
                ('cp1252', 'Windows-1252 (pt-BR)'),  # Most common in Brazil
                ('iso-8859-1', 'ISO-8859-1 (Latin-1)')
            ]

            # Try common delimiters (semicolon is standard in Brazil)
            delimiters = [';', ',', '\t']

            preview_loaded = False
            used_encoding = None
            used_delimiter = None

            for encoding, encoding_name in encodings:
                if preview_loaded:
                    break
                for delimiter in delimiters:
                    # Try different skip_rows values for files with metadata headers
                    skip_rows_options = [0, 5]  # 0 = no skip, 5 = skip metadata (account extract)

                    for skip_rows in skip_rows_options:
                        try:
                            uploaded_file.seek(0)
                            df_raw = pd.read_csv(
                                uploaded_file,
                                nrows=10,
                                encoding=encoding,
                                sep=delimiter,
                                decimal=',',  # Brazilian format uses comma for decimals
                                thousands='.',  # Brazilian format uses period for thousands
                                skiprows=skip_rows,
                                on_bad_lines='skip'
                            )
                            # Check if we got meaningful data (more than 1 column)
                            if len(df_raw.columns) > 1:
                                st.dataframe(df_raw, use_container_width=True)
                                used_encoding = encoding_name
                                used_delimiter = delimiter
                                preview_loaded = True
                                break
                        except (UnicodeDecodeError, pd.errors.ParserError):
                            continue
                        except Exception:
                            continue

                    if preview_loaded:
                        break

            if preview_loaded:
                info_parts = []
                if used_encoding != 'UTF-8':
                    info_parts.append(f"Codificação: {used_encoding}")
                if used_delimiter != ',':
                    delimiter_name = {';': 'ponto-e-vírgula', '\t': 'tab'}
                    info_parts.append(f"Delimitador: {delimiter_name.get(used_delimiter, used_delimiter)}")
                if info_parts:
                    st.info(f"Arquivo carregado com {' | '.join(info_parts)}")
            else:
                try:
                    uploaded_file.seek(0)
                    # Last resort: try to read as text and show error
                    content = uploaded_file.read(500).decode('utf-8', errors='replace')
                    st.error(f"Não foi possível interpretar o arquivo CSV. Primeiras linhas:\n```\n{content}\n```")
                except Exception as e:
                    st.error(f"Erro ao visualizar arquivo: {type(e).__name__} - {str(e)}")

        st.markdown("---")
        st.markdown("### Passo 2: Revisar Itens de Transação")

        # Parse the file
        if st.button("Analisar CSV", type="primary"):
            with st.spinner("Processando arquivo CSV..."):
                try:
                    uploaded_file.seek(0)
                    preview = api.preview_csv(uploaded_file)

                    # Store in session state
                    st.session_state["csv_preview"] = preview
                    st.success(f"✅ Analisados {preview['total_items']} itens")

                except Exception as e:
                    st.error(f"Erro ao analisar CSV: {str(e)}")
                    return

    # Show preview if available
    if "csv_preview" in st.session_state:
        preview = st.session_state["csv_preview"]

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Items", preview["total_items"])

        with col2:
            st.metric("Novos", preview["new_count"], help="Items ready to import")

        with col3:
            st.metric("Ignorados", preview["ignored_count"], help="In ignore list")

        with col4:
            st.metric("Duplicados", preview["duplicate_count"], help="Already imported")

        st.markdown("---")

        # Show items table with action selection
        st.markdown("### Selecione as Ações para cada Item")

        st.info("""
        **Ações:**
        - 📥 **Importar**: Importar normalmente.
        - 🔄 **Subscription**: Cria assinatura e importa.
        - 🚫 **Ignorar Desta Vez**: Ignora somente dessa vez.
        - ⛔ **Ignorar Sempre**: Ignora dessa vez e adiciona na lista de ignorados para todas as ocorrências futuras.
        - ✏️ **Sobrescrever**: Sobrescreve transação duplicada existente com os novos dados.
        """)

        # Create DataFrame for display
        items = preview["items"]
        df_items = pd.DataFrame(items)

        # Initialize actions in session state if not present
        if "item_actions" not in st.session_state:
            st.session_state["item_actions"] = {}

        # Initialize name mapping acceptances if not present
        if "mapping_acceptances" not in st.session_state:
            st.session_state["mapping_acceptances"] = {}

        # Display items with action selectors
        for idx, item in enumerate(items):
            # Determine default action and styling
            if item["is_ignored"]:
                default_action = "Skip (Ignored)"
                disabled = True
                is_duplicate = False
            elif item["is_duplicate"]:
                default_action = "ignore_once"  # Default to keeping existing
                disabled = False
                is_duplicate = True
            else:
                default_action = "import"
                disabled = False
                is_duplicate = False

            # Create container for each item
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 2])

                with col1:
                    if not disabled:
                        # Show name mapping suggestion if available
                        has_mapping = bool(item.get('suggested_name'))

                        # Initialize manual edit state if not present
                        if f"manual_edited_{idx}" not in st.session_state:
                            st.session_state[f"manual_edited_{idx}"] = False

                        # Determine display value for editable field
                        if st.session_state[f"manual_edited_{idx}"]:
                            # Use the manually edited value
                            default_value = st.session_state.get(f"manual_edit_{idx}", item['description'])
                        elif has_mapping and st.session_state.get("mapping_acceptances", {}).get(idx, False):
                            # Use the mapped name
                            default_value = item['suggested_name']
                        else:
                            # Use original description
                            default_value = item['description']

                        # Editable description field (looks like text but is editable on click)
                        edited_desc = st.text_input(
                            "Description",
                            value=default_value,
                            key=f"manual_edit_{idx}",
                            label_visibility="collapsed",
                            help="Click to edit the transaction description"
                        )

                        # Check if user has edited the description
                        if edited_desc != default_value:
                            st.session_state[f"manual_edited_{idx}"] = True

                        # Show name mapping suggestion if available and not manually edited
                        if has_mapping and not st.session_state[f"manual_edited_{idx}"]:
                            # Initialize acceptance state if not present
                            if idx not in st.session_state["mapping_acceptances"]:
                                st.session_state["mapping_acceptances"][idx] = False

                            # Show mapping hint and acceptance checkbox
                            accept_mapping = st.checkbox(
                                f"✏️ Rename as: **{item['suggested_name']}**",
                                value=st.session_state["mapping_acceptances"][idx],
                                key=f"accept_mapping_{idx}",
                                help="Accept this name mapping from your history"
                            )
                            st.session_state["mapping_acceptances"][idx] = accept_mapping

                        st.caption(f"{item['date']} • {item['source_type']}")

                        # Determine final description based on choices
                        if st.session_state[f"manual_edited_{idx}"]:
                            final_desc = edited_desc
                        elif has_mapping and st.session_state["mapping_acceptances"].get(idx, False):
                            final_desc = item['suggested_name']
                        else:
                            final_desc = None  # Use original

                        # Store edited description and flag in item_actions
                        if idx in st.session_state.get("item_actions", {}):
                            st.session_state["item_actions"][idx]["edited_description"] = final_desc
                            st.session_state["item_actions"][idx]["was_manually_edited"] = st.session_state[f"manual_edited_{idx}"]
                    else:
                        st.markdown(f"**{item['description']}**")
                        st.caption(f"{item['date']} • {item['source_type']}")

                with col2:
                    # Display amount exactly as parsed from CSV (no sign inversion)
                    st.markdown(f"**R$ {item['amount']:,.2f}**")
                    if item.get("transaction_type"):
                        st.caption(item["transaction_type"])

                with col3:
                    if item["is_ignored"]:
                        st.markdown("🚫 Ignored")
                    elif item["is_duplicate"]:
                        st.markdown("⚠️ **Duplicate**")
                    else:
                        st.markdown("✅ New")

                with col4:
                    if not disabled:
                        # Different options for duplicates vs new items
                        if is_duplicate:
                            # For duplicates: only ignore or overwrite
                            action_options = ["ignore_once", "overwrite"]
                            action_labels = {
                                "ignore_once": "🚫 Ignore (Keep Existing)",
                                "overwrite": "✏️ Overwrite"
                            }
                        else:
                            # For new items: full options
                            action_options = ["import", "subscription", "ignore_once", "ignore_always"]
                            action_labels = {
                                "import": "📥 Import",
                                "subscription": "🔄 Subscription",
                                "ignore_once": "🚫 Ignore Once",
                                "ignore_always": "⛔ Ignore Always"
                            }

                        action = st.selectbox(
                            "Action",
                            options=action_options,
                            format_func=lambda x, labels=action_labels: labels[x],
                            key=f"action_{idx}",
                            label_visibility="collapsed"
                        )

                        # Initialize action data if not exists
                        if idx not in st.session_state["item_actions"]:
                            st.session_state["item_actions"][idx] = {}

                        # Store action
                        st.session_state["item_actions"][idx]["action"] = action
                        st.session_state["item_actions"][idx]["subscription_name"] = None

                        # If subscription, ask for name
                        if action == "subscription":
                            sub_name = st.text_input(
                                "Subscription name",
                                value=item["description"][:50],
                                key=f"sub_name_{idx}",
                                label_visibility="collapsed"
                            )
                            st.session_state["item_actions"][idx]["subscription_name"] = sub_name

                    else:
                        st.markdown(default_action)

                st.markdown("---")

        # Confirm import button
        st.markdown("### Passo 3: Confirmar Importação")

        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("🚀 Confirmar Importação", type="primary", disabled=len(st.session_state.get("item_actions", {})) == 0):
                with st.spinner("Importando transações..."):
                    try:
                        # Build import request
                        actions = []
                        for idx, item in enumerate(items):
                            action_data = st.session_state["item_actions"].get(idx)

                            if action_data:
                                actions.append({
                                    "index": item["index"],
                                    "action": action_data["action"],
                                    "edited_description": action_data.get("edited_description"),
                                    "subscription_name": action_data.get("subscription_name")
                                })

                        import_request = {
                            "source_file": uploaded_file.name if uploaded_file else "unknown",
                            "source_type": preview["source_type"],
                            "items": items,
                            "actions": actions
                        }

                        # Call import API
                        result = api.import_csv(import_request)

                        # Show results
                        st.success(f"""
                        ✅ **Importação Concluída!**

                        - ✅ Importados: {result['imported_count']}
                        - ✏️ Sobrescritos: {result.get('overwritten_count', 0)}
                        - 🔄 Assinaturas Criadas: {result['subscriptions_created']}
                        - 🚫 Ignorados Uma Vez: {result['ignored_once_count']}
                        - ⛔ Adicionados à Lista: {result['ignored_always_count']}
                        """)

                        if result.get("errors"):
                            with st.expander("⚠️ Ver Erros"):
                                for error in result["errors"]:
                                    st.warning(error)

                        # Clear session state
                        del st.session_state["csv_preview"]
                        del st.session_state["item_actions"]
                        if "mapping_acceptances" in st.session_state:
                            del st.session_state["mapping_acceptances"]

                        # Clear manual edit flags
                        keys_to_delete = [key for key in st.session_state.keys()
                                         if key.startswith("manual_edited_") or key.startswith("manual_edit_")]
                        for key in keys_to_delete:
                            del st.session_state[key]

                        st.balloons()

                    except Exception as e:
                        st.error(f"Erro ao importar: {str(e)}")

        with col2:
            if st.button("Cancelar"):
                # Clear session state
                if "csv_preview" in st.session_state:
                    del st.session_state["csv_preview"]
                if "item_actions" in st.session_state:
                    del st.session_state["item_actions"]
                if "mapping_acceptances" in st.session_state:
                    del st.session_state["mapping_acceptances"]

                # Clear manual edit flags
                keys_to_delete = [key for key in st.session_state.keys()
                                 if key.startswith("manual_edited_") or key.startswith("manual_edit_")]
                for key in keys_to_delete:
                    del st.session_state[key]

                st.rerun()

    else:
        st.info("Envie um arquivo CSV para comecar")

    # Show import history section
    st.markdown("---")
    show_import_history(api)

"""Database management component for export/import and backup operations."""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any


def render_database_manager(api):
    """
    Render database management interface.

    Features:
    - Export database to JSON
    - Import database from JSON with preview
    - Create and restore backups
    """
    st.markdown("### Database Export/Import")

    # Create tabs for different operations
    export_tab, import_tab, backup_tab = st.tabs([
        "📤 Export",
        "📥 Import",
        "💾 Backups"
    ])

    # Export Tab
    with export_tab:
        st.markdown("Export your entire database to a JSON file. This includes all transactions, "
                   "categories, subscriptions, income sources, and settings.")

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📤 Export Database", type="primary", use_container_width=True):
                try:
                    with st.spinner("Exporting database..."):
                        export_data = api.export_database()

                    # Create download button
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"dindinho_export_{timestamp}.json"

                    st.download_button(
                        label="⬇️ Download Export File",
                        data=json.dumps(export_data, indent=2, ensure_ascii=False),
                        file_name=filename,
                        mime="application/json",
                        use_container_width=True
                    )

                    # Show summary
                    metadata = export_data.get("metadata", {})
                    st.success("Database exported successfully!")
                    st.info(
                        f"**Export Summary:**\n\n"
                        f"- Transactions: {metadata.get('total_transactions', 0)}\n"
                        f"- Categories: {metadata.get('total_categories', 0)}\n"
                        f"- Subscriptions: {metadata.get('total_subscriptions', 0)}\n"
                        f"- Income Sources: {metadata.get('total_income_sources', 0)}"
                    )

                except Exception as e:
                    st.error(f"Export failed: {str(e)}")

    # Import Tab
    with import_tab:
        st.markdown("Import data from a JSON export file. This will merge the imported data with "
                   "your existing database, skipping duplicates.")

        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a JSON export file",
            type=["json"],
            help="Upload a database export file created by the export feature"
        )

        if uploaded_file is not None:
            try:
                # Parse JSON
                uploaded_file.seek(0)
                import_data = json.load(uploaded_file)

                # Preview import
                with st.spinner("Analyzing import file..."):
                    preview = api.preview_database_import(import_data)

                if not preview.get("valid"):
                    st.error("Invalid import file!")
                    errors = preview.get("errors", [])
                    for error in errors:
                        st.error(f"- {error}")
                else:
                    # Show preview
                    st.success("Import file is valid!")

                    # Show conflict summary
                    with st.expander("📊 Import Preview", expanded=True):
                        conflicts = preview.get("conflicts", {})

                        # Create summary table
                        summary_data = []
                        for table_name, conflict in conflicts.items():
                            # Format table name
                            display_name = table_name.replace("_", " ").title()
                            summary_data.append({
                                "Table": display_name,
                                "Total": conflict.get("total", 0),
                                "New": conflict.get("new", 0),
                                "Duplicates": conflict.get("duplicates", 0)
                            })

                        st.table(summary_data)

                        st.info(
                            f"**Total:** {preview.get('total_new_records', 0)} new records will be imported, "
                            f"{preview.get('total_skipped_records', 0)} duplicates will be skipped."
                        )

                    # Import options
                    st.markdown("---")
                    st.markdown("**Import Options:**")

                    create_backup = st.checkbox(
                        "Create backup before import",
                        value=True,
                        help="Recommended: Create a backup before importing to allow rollback"
                    )

                    # Confirmation
                    st.warning(
                        "⚠️ **Warning:** This operation will add new data to your database. "
                        "Duplicates will be skipped based on date, description, and amount."
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Execute Import", type="primary", use_container_width=True):
                            try:
                                with st.spinner("Importing data..."):
                                    result = api.execute_database_import(
                                        data=import_data,
                                        create_backup=create_backup
                                    )

                                if result.get("success"):
                                    st.success("Import completed successfully!")

                                    # Show import statistics
                                    imported = result.get("imported", {})
                                    skipped = result.get("skipped", {})

                                    with st.expander("📈 Import Results", expanded=True):
                                        result_data = []
                                        for table_name in set(list(imported.keys()) + list(skipped.keys())):
                                            display_name = table_name.replace("_", " ").title()
                                            result_data.append({
                                                "Table": display_name,
                                                "Imported": imported.get(table_name, 0),
                                                "Skipped": skipped.get(table_name, 0)
                                            })

                                        st.table(result_data)

                                    if result.get("backup_file"):
                                        st.info(f"Backup created: {result.get('backup_file')}")

                                    # Force page refresh to show new data
                                    st.rerun()
                                else:
                                    st.error("Import failed!")
                                    errors = result.get("errors", [])
                                    for error in errors:
                                        st.error(f"- {error}")

                            except Exception as e:
                                st.error(f"Import failed: {str(e)}")

                    with col2:
                        if st.button("❌ Cancel", use_container_width=True):
                            st.rerun()

            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid database export file.")
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

    # Backup Tab
    with backup_tab:
        st.markdown("Manage database backups. Create manual backups or restore from previous backups.")

        # Create backup section
        st.markdown("#### Create Backup")
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("💾 Create Backup", use_container_width=True):
                try:
                    with st.spinner("Creating backup..."):
                        result = api.create_backup()

                    if result.get("success"):
                        st.success(result.get("message", "Backup created successfully!"))
                        st.info(f"Backup file: {result.get('backup_file')}")
                        st.rerun()  # Refresh to show new backup in list
                    else:
                        st.error("Backup creation failed!")

                except Exception as e:
                    st.error(f"Backup failed: {str(e)}")

        # List backups section
        st.markdown("---")
        st.markdown("#### Available Backups")

        try:
            backups_response = api.list_backups()
            backups = backups_response.get("backups", [])

            if not backups:
                st.info("No backups found. Create your first backup above.")
            else:
                # Show backups in a table with restore buttons
                for backup in backups:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                        with col1:
                            st.text(backup.get("filename"))

                        with col2:
                            created_at = datetime.fromisoformat(backup.get("created_at"))
                            st.text(created_at.strftime("%Y-%m-%d %H:%M:%S"))

                        with col3:
                            size_bytes = backup.get("size_bytes", 0)
                            size_kb = size_bytes / 1024
                            if size_kb > 1024:
                                size_str = f"{size_kb / 1024:.2f} MB"
                            else:
                                size_str = f"{size_kb:.2f} KB"
                            st.text(size_str)

                        with col4:
                            # Use unique key for each button
                            restore_key = f"restore_{backup.get('filename')}"
                            if st.button("🔄 Restore", key=restore_key, use_container_width=True):
                                # Confirmation dialog
                                st.session_state[f"confirm_restore_{backup.get('filename')}"] = True

                        # Show confirmation dialog if restore was clicked
                        if st.session_state.get(f"confirm_restore_{backup.get('filename')}"):
                            with st.container():
                                st.warning(
                                    f"⚠️ **Warning:** Restoring this backup will replace your current database. "
                                    f"This operation cannot be undone!"
                                )

                                col1, col2 = st.columns(2)
                                with col1:
                                    confirm_key = f"confirm_yes_{backup.get('filename')}"
                                    if st.button("✅ Yes, Restore", key=confirm_key, type="primary"):
                                        try:
                                            with st.spinner("Restoring backup..."):
                                                result = api.restore_backup(backup.get("filename"))

                                            if result.get("success"):
                                                st.success(result.get("message", "Backup restored successfully!"))
                                                # Clear confirmation state
                                                del st.session_state[f"confirm_restore_{backup.get('filename')}"]
                                                st.rerun()
                                            else:
                                                st.error("Restore failed!")

                                        except Exception as e:
                                            st.error(f"Restore failed: {str(e)}")

                                with col2:
                                    cancel_key = f"confirm_no_{backup.get('filename')}"
                                    if st.button("❌ Cancel", key=cancel_key):
                                        # Clear confirmation state
                                        del st.session_state[f"confirm_restore_{backup.get('filename')}"]
                                        st.rerun()

                        st.markdown("---")

        except Exception as e:
            st.error(f"Failed to load backups: {str(e)}")

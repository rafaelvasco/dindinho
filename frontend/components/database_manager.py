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

                    # Show summary first
                    metadata = export_data.get("metadata", {})
                    st.success(
                        f"✅ **Database exported successfully!**\n\n"
                        f"📊 **Export Summary:**\n"
                        f"- {metadata.get('total_transactions', 0)} transactions\n"
                        f"- {metadata.get('total_categories', 0)} categories\n"
                        f"- {metadata.get('total_subscriptions', 0)} subscriptions\n"
                        f"- {metadata.get('total_income_sources', 0)} income sources"
                    )

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

                    st.info("💡 **Tip:** Save this file securely. You can use it to import data into another environment.")

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
                                    # Show import statistics
                                    imported = result.get("imported", {})
                                    skipped = result.get("skipped", {})

                                    total_imported = sum(imported.values())
                                    total_skipped = sum(skipped.values())

                                    # Clear, prominent success message with summary
                                    st.success(
                                        f"✅ **Import completed successfully!**\n\n"
                                        f"📊 **Summary:**\n"
                                        f"- {total_imported} records imported\n"
                                        f"- {total_skipped} duplicates skipped"
                                    )

                                    # Show detailed breakdown
                                    with st.expander("📈 Detailed Import Results", expanded=False):
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
                                        st.info(f"💾 Backup created: {result.get('backup_file')}")

                                    # Show button to refresh and see new data
                                    if st.button("🔄 Refresh Page to See New Data", type="primary", use_container_width=True):
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
                        st.success(
                            f"✅ **Backup created successfully!**\n\n"
                            f"💾 {result.get('backup_file')}"
                        )
                        st.info("💡 **Tip:** Backups are stored in `data/backups/` directory")

                        # Show button to refresh backup list
                        if st.button("🔄 Refresh Backup List", use_container_width=True):
                            st.rerun()
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
                                                st.success(
                                                    f"✅ **Database restored successfully!**\n\n"
                                                    f"Your database has been restored from:\n"
                                                    f"💾 {backup.get('filename')}"
                                                )
                                                st.info("💡 **Note:** The application will reload to reflect the restored data")

                                                # Clear confirmation state
                                                del st.session_state[f"confirm_restore_{backup.get('filename')}"]

                                                # Show button to reload
                                                if st.button("🔄 Reload Application", type="primary", use_container_width=True):
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

    # Dangerous Operations Section
    st.markdown("---")
    st.markdown("---")
    st.markdown("## ⚠️ Dangerous Operations")

    with st.expander("🗑️ Clear Database (Delete All Data)", expanded=False):
        st.error(
            "**⚠️ DANGER: This operation will permanently delete ALL data from your database!**\n\n"
            "This includes:\n"
            "- All transactions\n"
            "- All subscriptions\n"
            "- All income sources\n"
            "- All ignored patterns\n"
            "- All name mappings\n\n"
            "**This action cannot be undone!**"
        )

        st.markdown("---")

        # Initialize session state for clear database flow
        if "clear_db_step" not in st.session_state:
            st.session_state.clear_db_step = 0

        if st.session_state.clear_db_step == 0:
            # Step 1: Initial warning
            st.warning("Before proceeding, make sure you have a recent backup of your data.")

            create_backup_before_clear = st.checkbox(
                "Create automatic backup before clearing",
                value=True,
                help="Strongly recommended: Create a backup before deleting all data",
                key="clear_db_create_backup"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Proceed to Confirmation", type="primary", use_container_width=True):
                    st.session_state.clear_db_step = 1
                    st.rerun()

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.clear_db_step = 0
                    st.rerun()

        elif st.session_state.clear_db_step == 1:
            # Step 2: Type confirmation text
            st.error("**FINAL WARNING:** You are about to delete all data!")

            st.markdown("To confirm, please type the following text exactly:")
            st.code("DELETE ALL DATA", language=None)

            confirmation_text = st.text_input(
                "Type confirmation text:",
                key="clear_db_confirmation_text",
                placeholder="DELETE ALL DATA"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear Database Now", type="primary", use_container_width=True):
                    if confirmation_text == "DELETE ALL DATA":
                        # Proceed with clearing
                        try:
                            with st.spinner("Clearing database..."):
                                result = api.clear_database(
                                    confirmation_text=confirmation_text,
                                    create_backup=st.session_state.get("clear_db_create_backup", True)
                                )

                            if result.get("success"):
                                records_deleted = result.get("records_deleted", {})
                                total_deleted = sum(records_deleted.values())

                                st.success(
                                    f"✅ **Database cleared successfully!**\n\n"
                                    f"📊 **Summary:**\n"
                                    f"- {total_deleted} total records deleted"
                                )

                                if result.get("backup_file"):
                                    st.info(f"💾 Backup created: {result.get('backup_file')}")

                                # Show detailed breakdown
                                with st.expander("📈 Detailed Deletion Results", expanded=False):
                                    for table_name, count in records_deleted.items():
                                        display_name = table_name.replace("_", " ").title()
                                        st.write(f"- **{display_name}**: {count} records")

                                st.warning("💡 **Note:** The application will reload to reflect the cleared database")

                                # Reset step
                                st.session_state.clear_db_step = 0

                                # Show button to reload
                                if st.button("🔄 Reload Application", type="primary", use_container_width=True):
                                    st.rerun()
                            else:
                                st.error("Database clear failed!")

                        except Exception as e:
                            st.error(f"Clear failed: {str(e)}")
                            st.session_state.clear_db_step = 0
                    else:
                        st.error("❌ Confirmation text does not match. Please type 'DELETE ALL DATA' exactly.")

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.clear_db_step = 0
                    st.rerun()

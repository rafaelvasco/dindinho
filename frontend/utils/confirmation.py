"""Reusable confirmation dialog utilities for Streamlit."""

import streamlit as st
from typing import Callable, Optional


class ConfirmationDialog:
    """Manages confirmation dialogs using Streamlit's modal dialog feature."""

    @staticmethod
    def show_delete_confirmation(
        item_name: str,
        on_confirm: Callable,
        title: str = "Confirm Deletion",
        message: Optional[str] = None,
        confirm_label: str = "Delete",
        cancel_label: str = "Cancel"
    ):
        """
        Show a modal confirmation dialog for delete operations.

        Args:
            item_name: Name/description of item to delete
            on_confirm: Callback function to execute when confirmed
            title: Dialog title
            message: Custom message (if None, uses default)
            confirm_label: Label for confirm button
            cancel_label: Label for cancel button

        Usage:
            if st.button("Delete"):
                ConfirmationDialog.show_delete_confirmation(
                    item_name="this subscription",
                    on_confirm=lambda: api.delete_subscription(sub_id)
                )
        """
        @st.dialog(title)
        def confirm_dialog():
            # Show warning message
            if message:
                st.warning(message)
            else:
                st.warning(f"Are you sure you want to delete **{item_name}**?")
                st.markdown("This action cannot be undone.")

            # Buttons
            col1, col2 = st.columns(2)

            with col1:
                if st.button(confirm_label, type="primary", use_container_width=True):
                    on_confirm()
                    st.rerun()

            with col2:
                if st.button(cancel_label, use_container_width=True):
                    st.rerun()

        # Open the dialog
        confirm_dialog()

import streamlit as st
from utils.api_client import get_api_client


def render_category_pills():
    """
    Renders a horizontal row of clickable category pills for filtering.
    Stores selected category in session state and returns it.

    Returns:
        str: Selected category name or None if "All" is selected
    """
    # Initialize session state for selected category if not present
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = "All"

    # Fetch categories from API
    api = get_api_client()
    try:
        response = api.get_transactions_by_category()
        categories = ["All"] + [item["category"] for item in response["categories"]]
    except Exception as e:
        st.error(f"Failed to load categories: {str(e)}")
        categories = ["All"]

    # Custom CSS for pills
    st.markdown("""
        <style>
        .category-pills-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 16px 0;
            align-items: center;
        }
        .category-pill {
            padding: 6px 16px;
            border-radius: 20px;
            border: 2px solid #ddd;
            background-color: #f8f9fa;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 14px;
            font-weight: 500;
            white-space: nowrap;
        }
        .category-pill:hover {
            border-color: #4CAF50;
            background-color: #e8f5e9;
        }
        .category-pill.active {
            border-color: #4CAF50;
            background-color: #4CAF50;
            color: white;
        }
        .filter-label {
            font-weight: 600;
            color: #555;
            margin-right: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Display category pills
    st.markdown("**Filter by Category:**")

    # Create columns for pills (use dynamic number based on category count)
    num_cols = min(len(categories), 8)  # Max 8 pills per row
    cols = st.columns(num_cols)

    # Handle category selection
    for idx, category in enumerate(categories[:num_cols]):
        col_idx = idx % num_cols
        with cols[col_idx]:
            is_selected = st.session_state.selected_category == category
            button_type = "primary" if is_selected else "secondary"
            if st.button(
                category,
                key=f"cat_pill_{category}",
                use_container_width=True,
                type=button_type,
                help=f"Filter by {category}" if category != "All" else "Show all categories"
            ):
                st.session_state.selected_category = category
                st.rerun()

    # If there are more categories, show them in additional rows
    if len(categories) > num_cols:
        remaining_categories = categories[num_cols:]
        num_rows = (len(remaining_categories) + num_cols - 1) // num_cols

        for row in range(num_rows):
            start_idx = row * num_cols
            end_idx = min(start_idx + num_cols, len(remaining_categories))
            row_categories = remaining_categories[start_idx:end_idx]

            cols = st.columns(num_cols)
            for idx, category in enumerate(row_categories):
                with cols[idx]:
                    is_selected = st.session_state.selected_category == category
                    button_type = "primary" if is_selected else "secondary"
                    if st.button(
                        category,
                        key=f"cat_pill_{category}",
                        use_container_width=True,
                        type=button_type,
                        help=f"Filter by {category}"
                    ):
                        st.session_state.selected_category = category
                        st.rerun()

    # Return None if "All" is selected, otherwise return the category name
    return None if st.session_state.selected_category == "All" else st.session_state.selected_category

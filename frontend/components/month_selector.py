import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta


def render_month_selector():
    """
    Renders a month/year selector with back/forward navigation buttons.
    Stores selected month/year in session state and returns start_date/end_date
    for API calls.

    Returns:
        tuple: (start_date, end_date) representing the first and last day of the selected month
    """
    # Initialize session state for month/year if not present
    if 'selected_month' not in st.session_state:
        # Default to current month
        now = datetime.now()
        st.session_state.selected_month = now.month
        st.session_state.selected_year = now.year

    # Create three columns: back button, month/year display, forward button
    col1, col2, col3 = st.columns([1, 6, 1])

    with col1:
        if st.button("◀", key="prev_month", use_container_width=True, help="Previous month"):
            # Go back one month
            current = datetime(st.session_state.selected_year, st.session_state.selected_month, 1)
            previous = current - relativedelta(months=1)
            st.session_state.selected_month = previous.month
            st.session_state.selected_year = previous.year
            st.rerun()

    with col2:
        # Display current month and year prominently
        current_date = datetime(st.session_state.selected_year, st.session_state.selected_month, 1)
        month_year_str = current_date.strftime("%B %Y")
        st.markdown(f"<h2 style='text-align: center; margin: 0;'>{month_year_str}</h2>",
                   unsafe_allow_html=True)

    with col3:
        if st.button("▶", key="next_month", use_container_width=True, help="Next month"):
            # Go forward one month
            current = datetime(st.session_state.selected_year, st.session_state.selected_month, 1)
            next_month = current + relativedelta(months=1)
            st.session_state.selected_month = next_month.month
            st.session_state.selected_year = next_month.year
            st.rerun()

    # Calculate start_date and end_date for the selected month
    start_date = datetime(st.session_state.selected_year, st.session_state.selected_month, 1).date()
    # Get the last day of the month
    next_month_first = datetime(st.session_state.selected_year, st.session_state.selected_month, 1) + relativedelta(months=1)
    end_date = (next_month_first - relativedelta(days=1)).date()

    return start_date, end_date

"""
Enterprise Employee Analytics & Data Warehouse System
Phase 4: Streamlit Web Application

Strictly streamlined and focused on the two deliverables required:
1. Analytics Dashboard (OLAP Interaction):
   - Direct connection to Data Warehouse (Star Schema)
   - Interactive charts:
     - High-level KPIs
     - Top-performing employees by department (SQL Window Function DENSE_RANK)
     - Year-over-year performance & salary trends (SQL Window Function LAG)
     - Employee attrition risk & bottlenecks (SQL Window Function NTILE 4)

2. Data Entry Module (OLTP Interaction & SCD Type 2):
   - Forms to onboard new employees, create projects, and submit performance reviews
   - Form to update employee department and role, triggering SCD Type 2 history in Data Warehouse
"""

import sys
from pathlib import Path

# Ensure workspace root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from app.config import APP_TITLE, APP_SUBTITLE, APP_ICON, PAGES
from app.auth import AuthenticationManager
from app.data_provider import DataProvider
from app.utils.ui_helpers import apply_custom_css
from app.views.authentication import render_authentication_page
from app.views.analytics_dashboard import render_analytics_dashboard
from app.views.data_entry_module import render_data_entry_module
from app.views.read_only_data import render_read_only_data


def main():
    """Main application lifecycle and page routing."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Apply clean corporate theme
    apply_custom_css()

    # Initialize shared DataProvider in session state
    if "data_provider" not in st.session_state:
        st.session_state.data_provider = DataProvider()

    provider: DataProvider = st.session_state.data_provider
    try:
        if "auth_manager" not in st.session_state:
            st.session_state.auth_manager = AuthenticationManager(provider.db)
    except SQLAlchemyError as ex:
        st.error(f"Unable to connect to the account database: {ex}")
        st.info("Check MySQL availability, database credentials, and CREATE TABLE permissions for enterprise_oltp.")
        st.stop()

    user = st.session_state.get("current_user")
    if not user:
        render_authentication_page(st.session_state.auth_manager)
        return

    # -------------------------------------------------------------------------
    # Sidebar Navigation & Diagnostics
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.markdown(f"## {APP_ICON} {APP_TITLE}")
        st.caption(APP_SUBTITLE)
        st.write(f"Signed in as **{user['full_name']}**")
        st.caption("HR" if user["role"] == "hr" else "Read-only")
        if st.button("Sign out", use_container_width=True):
            del st.session_state["current_user"]
            st.rerun()
        st.divider()

        # Database Status Badge
        if provider.is_live:
            st.success("🟢 **Live MySQL Connected**\n`enterprise_oltp` & `enterprise_dw` active")
        else:
            st.info("ℹ️ **Interactive Demo Mode**\nRunning on synthesized warehouse dataset (100k+ records).")

        st.divider()

        # Page Navigation (Simple 2-Module Selection)
        pages = PAGES if user["role"] == "hr" else {
            "analytics_dashboard": PAGES["analytics_dashboard"],
            "read_only_data": "📚 Organization Data (Read-only)",
        }
        selected_page_key = st.radio(
            "🧭 Select Project Module:",
            options=list(pages.keys()),
            format_func=lambda k: pages[k],
            index=0,
        )



    # -------------------------------------------------------------------------
    # Page Routing
    # -------------------------------------------------------------------------
    if selected_page_key == "analytics_dashboard":
        render_analytics_dashboard(provider)
    elif selected_page_key == "data_entry_module":
        render_data_entry_module(provider, user["role"])
    elif selected_page_key == "read_only_data":
        render_read_only_data(provider)


if __name__ == "__main__":
    main()

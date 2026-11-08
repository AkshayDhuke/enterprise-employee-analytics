"""
Enterprise Employee Analytics & Data Warehouse System
Phase 4: Interactive Executive Streamlit Application

Entry point for corporate dashboard, analytical SQL window function visualizations,
OLTP HR management, and SCD Type 2 dimension lifecycle tracking.
"""

import sys
from pathlib import Path

# Ensure workspace root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from app.config import APP_TITLE, APP_SUBTITLE, APP_ICON, PAGES
from app.data_provider import DataProvider
from app.utils.ui_helpers import apply_custom_css
from app.views.executive_kpi import render_executive_kpi_view
from app.views.analytics_hub import render_analytics_hub_view
from app.views.employee_mgmt import render_employee_mgmt_view
from app.views.project_mgmt import render_project_mgmt_view
from app.views.review_mgmt import render_review_mgmt_view
from app.views.database_admin import render_database_admin_view


def main():
    """Main application lifecycle and page routing."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Apply corporate theme
    apply_custom_css()

    # Initialize shared DataProvider in session state
    if "data_provider" not in st.session_state:
        st.session_state.data_provider = DataProvider()

    provider: DataProvider = st.session_state.data_provider

    # -------------------------------------------------------------------------
    # Sidebar Navigation & Diagnostics
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.markdown(f"## {APP_ICON} {APP_TITLE}")
        st.caption(APP_SUBTITLE)
        st.divider()

        # Database Status Badge
        if provider.is_live:
            st.success("🟢 **Live MySQL Connected**\n`enterprise_oltp` & `enterprise_dw` active")
        else:
            st.warning("🟡 **Interactive Demo Mode**\nMySQL offline. Running on synthetic OLAP dataset.")

        st.divider()

        # Page Navigation
        selected_page_key = st.radio(
            "🧭 System Navigation:",
            options=list(PAGES.keys()),
            format_func=lambda k: PAGES[k],
            index=0,
        )

        st.divider()

        # Sidebar Footer
        st.caption("🏢 **Enterprise Data Platform** | v4.0.0")
        st.caption("Phase 4: Streamlit UI & Analytical Dashboards")

    # -------------------------------------------------------------------------
    # Page Routing
    # -------------------------------------------------------------------------
    if selected_page_key == "kpi_overview":
        render_executive_kpi_view(provider)
    elif selected_page_key == "advanced_analytics":
        render_analytics_hub_view(provider)
    elif selected_page_key == "employee_ops":
        render_employee_mgmt_view(provider)
    elif selected_page_key == "project_allocations":
        render_project_mgmt_view(provider)
    elif selected_page_key == "review_hub":
        render_review_mgmt_view(provider)
    elif selected_page_key == "warehouse_admin":
        render_database_admin_view(provider)


if __name__ == "__main__":
    main()

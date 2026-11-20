"""Read-only directory views for authenticated non-HR users."""

import pandas as pd
import streamlit as st

from app.data_provider import DataProvider


def render_read_only_data(provider: DataProvider) -> None:
    st.title("📚 Organization Data")
    st.caption("Browse employee and project records. Only HR accounts can make changes.")

    employee_tab, project_tab = st.tabs(["Employees", "Projects"])
    with employee_tab:
        search_term = st.text_input("Search employees by name, email, role, or ID")
        employees = provider.get_all_employees(
            limit=1000,
            search_term=search_term.strip() or None,
        )
        if employees:
            st.dataframe(pd.DataFrame(employees), use_container_width=True, hide_index=True)
        else:
            st.info("No employee records match your search.")

    with project_tab:
        projects = provider.get_all_projects()
        if projects:
            st.dataframe(pd.DataFrame(projects), use_container_width=True, hide_index=True)
        else:
            st.info("No project records are available.")

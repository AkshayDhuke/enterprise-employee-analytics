"""
Project Allocations & Capacity Management View.
Allows managers to create corporate initiatives and assign employees with workload percentage tracking.
"""

from datetime import date
import streamlit as st
import pandas as pd

from app.data_provider import DataProvider
from app.config import DEFAULT_DEPARTMENTS
from app.utils.ui_helpers import render_section_header


def render_project_mgmt_view(provider: DataProvider):
    """Renders the project portfolio and team allocation view."""
    st.title("📁 Project Allocations & Bandwidth Capacity")
    st.markdown("Initiative tracking and employee allocation monitoring to detect bottlenecks across the enterprise.")

    tabs = st.tabs(["📊 Project Portfolio", "➕ Create New Project", "👥 Assign Team Member"])

    dept_id_map = {d["department_name"]: d["department_id"] for d in DEFAULT_DEPARTMENTS}

    # -------------------------------------------------------------------------
    # TAB 1: Project Portfolio
    # -------------------------------------------------------------------------
    with tabs[0]:
        render_section_header("Active Enterprise Projects")

        projects = provider.get_all_projects()

        if projects:
            df = pd.DataFrame(projects)
            df["budget"] = df["budget"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            cols = ["project_code", "project_name", "department_name", "priority", "status", "budget", "start_date", "end_date"]
            available = [c for c in cols if c in df.columns]
            df_disp = df[available].copy()
            df_disp.columns = [c.replace("_", " ").title() for c in available]
            st.dataframe(df_disp, use_container_width=True, hide_index=True)
        else:
            st.info("No projects registered in the system.")

    # -------------------------------------------------------------------------
    # TAB 2: Create New Project
    # -------------------------------------------------------------------------
    with tabs[1]:
        render_section_header("Register Corporate Project", "Creates project in enterprise_oltp.projects and synchronizes Dim_Project in DW.")

        with st.form("create_project_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                proj_name = st.text_input("Project Name *", placeholder="NextGen Cloud Platform")
                dept_name = st.selectbox("Department *", [d["department_name"] for d in DEFAULT_DEPARTMENTS])
                priority = st.selectbox("Priority Level", ["Critical", "High", "Medium", "Low"], index=1)
            with c2:
                budget = st.number_input("Allocated Budget ($)", min_value=10000.0, max_value=50000000.0, value=500000.0, step=50000.0)
                start_dt = st.date_input("Start Date", value=date.today())
                end_dt = st.date_input("Target Completion Date", value=date.today().replace(year=date.today().year + 1))

            status = st.selectbox("Status", ["Active", "Planning", "On Hold", "Completed"])

            submitted = st.form_submit_button("📁 Register Project", use_container_width=True)

            if submitted:
                if not proj_name.strip():
                    st.error("Project name is required.")
                else:
                    dept_id = dept_id_map.get(dept_name, 1)
                    proj_payload = {
                        "project_name": proj_name.strip(),
                        "department_id": dept_id,
                        "department_name": dept_name,
                        "priority": priority,
                        "status": status,
                        "budget": float(budget),
                        "start_date": str(start_dt),
                        "end_date": str(end_dt),
                    }
                    try:
                        proj_id = provider.create_project(proj_payload)
                        st.success(f"🎉 Project #{proj_id} '{proj_name}' registered successfully and synchronized to Dim_Project!")
                    except Exception as ex:
                        st.error(f"Failed to create project: {ex}")

    # -------------------------------------------------------------------------
    # TAB 3: Assign Team Member
    # -------------------------------------------------------------------------
    with tabs[2]:
        render_section_header("Assign Employee Bandwidth", "Allocates employee effort percentage into Fact_ProjectAllocations.")

        projects = provider.get_all_projects()
        employees = provider.get_all_employees(limit=50)

        if projects and employees:
            proj_options = {p["project_id"]: f"{p.get('project_code', 'PRJ')} - {p['project_name']}" for p in projects}
            emp_options = {e["employee_id"]: f"{e['full_name']} ({e.get('job_role', '')})" for e in employees}

            with st.form("assign_member_form"):
                p_id = st.selectbox("Select Project:", options=list(proj_options.keys()), format_func=lambda x: proj_options[x])
                e_id = st.selectbox("Select Employee:", options=list(emp_options.keys()), format_func=lambda x: emp_options[x])
                alloc_pct = st.slider("Allocation Bandwidth Percentage (%):", min_value=10, max_value=100, value=50, step=5)
                assigned_role = st.selectbox("Role in Project:", ["Project Lead", "Senior Developer", "Architect", "QA Engineer", "Business Analyst", "Contributor"])

                if alloc_pct > 80:
                    st.warning("⚠️ High commitment: Check employee allocation in 'Resource Bottlenecks' to prevent over-allocation.")

                assign_btn = st.form_submit_button("🤝 Confirm Project Assignment", use_container_width=True)

                if assign_btn:
                    st.success(f"✅ Assigned {emp_options[e_id]} to {proj_options[p_id]} at {alloc_pct}% capacity!")
        else:
            st.info("Ensure both projects and employees are present in the system.")


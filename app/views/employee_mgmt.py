"""
Employee Management View (OLTP Operations & SCD Type 2 Lifecycle).
Enables HR staff to search employees, add new hires, and trigger SCD Type 2 promotions/transfers.
"""

from datetime import date
import streamlit as st
import pandas as pd

from app.data_provider import DataProvider
from app.config import DEFAULT_DEPARTMENTS, JOB_ROLES, EDUCATION_FIELDS
from app.utils.ui_helpers import render_section_header


def render_employee_mgmt_view(provider: DataProvider):
    """Renders the HR Employee management and SCD Type 2 lifecycle view."""
    st.title("👥 Employee Directory & SCD Type 2 Lifecycle")
    st.markdown("Transactional HR operations maintaining OLTP tables and synchronizing point-in-time SCD2 warehouse versions.")

    tabs = st.tabs(["📋 Employee Directory", "➕ Add New Hire", "🚀 Promote / Transfer (SCD Type 2)", "⚠️ Terminate / Attrition"])

    # -------------------------------------------------------------------------
    # TAB 1: Employee Directory & Search
    # -------------------------------------------------------------------------
    with tabs[0]:
        render_section_header("Active Workforce Directory")
        c1, c2 = st.columns([3, 1])
        with c1:
            search_query = st.text_input("🔍 Search by name, role, email, or employee #:", "")
        with c2:
            dept_filter = st.selectbox(
                "Filter Department:",
                ["All"] + [d["department_name"] for d in DEFAULT_DEPARTMENTS],
                key="emp_dir_dept",
            )

        dept_id_map = {d["department_name"]: d["department_id"] for d in DEFAULT_DEPARTMENTS}
        dept_id = dept_id_map.get(dept_filter) if dept_filter != "All" else None

        employees = provider.get_all_employees(limit=100, department_id=dept_id, search_term=search_query if search_query else None)

        if employees:
            df = pd.DataFrame(employees)
            df["monthly_income"] = df["monthly_income"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            cols = ["employee_number", "full_name", "department_name", "job_role", "job_level", "monthly_income", "email", "attrition", "hire_date"]
            available_cols = [c for c in cols if c in df.columns]
            df_disp = df[available_cols].copy()
            df_disp.columns = [c.replace("_", " ").title() for c in available_cols]
            st.dataframe(df_disp, use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(employees)} employee record(s).")
        else:
            st.info("No employees found matching the search criteria.")

    # -------------------------------------------------------------------------
    # TAB 2: Add New Hire
    # -------------------------------------------------------------------------
    with tabs[1]:
        render_section_header("Onboard New Employee", "Creates record in enterprise_oltp.employees and syncs Version 1 to Dim_Employee.")

        with st.form("add_employee_form", clear_on_submit=True):
            f1, f2 = st.columns(2)
            with f1:
                first_name = st.text_input("First Name *", placeholder="Jane")
                email = st.text_input("Corporate Email *", placeholder="jane.doe@enterprise.com")
                age = st.number_input("Age", min_value=18, max_value=75, value=28)
                dept_name = st.selectbox("Department *", [d["department_name"] for d in DEFAULT_DEPARTMENTS])
                job_level = st.selectbox("Job Level *", [1, 2, 3, 4, 5], index=1)
            with f2:
                last_name = st.text_input("Last Name *", placeholder="Doe")
                gender = st.selectbox("Gender", ["Female", "Male", "Other"])
                hire_date = st.date_input("Hire Date *", value=date.today())
                job_role = st.selectbox("Job Role *", JOB_ROLES)
                monthly_income = st.number_input("Monthly Income ($) *", min_value=1000.0, max_value=100000.0, value=6500.0, step=250.0)

            education = st.selectbox("Education Field", EDUCATION_FIELDS)

            submitted = st.form_submit_button("💼 Register New Employee", use_container_width=True)

            if submitted:
                if not first_name.strip() or not last_name.strip() or not email.strip():
                    st.error("Please fill in all required fields (First Name, Last Name, Email).")
                elif "@" not in email:
                    st.error("Invalid email format.")
                else:
                    dept_id_sel = dept_id_map.get(dept_name, 1)
                    new_emp_payload = {
                        "first_name": first_name.strip(),
                        "last_name": last_name.strip(),
                        "email": email.strip(),
                        "gender": gender,
                        "age": int(age),
                        "department_id": dept_id_sel,
                        "department_name": dept_name,
                        "job_role": job_role,
                        "job_level": int(job_level),
                        "monthly_income": float(monthly_income),
                        "education_field": education,
                        "years_at_company": 0,
                        "attrition": "No",
                        "hire_date": str(hire_date),
                    }
                    try:
                        new_id = provider.create_employee(new_emp_payload)
                        st.success(f"🎉 Successfully created Employee #{new_id} ({first_name} {last_name})! Synchronized baseline Version 1 into Dim_Employee.")
                    except Exception as ex:
                        st.error(f"Failed to create employee: {ex}")

    # -------------------------------------------------------------------------
    # TAB 3: Promote / Transfer (SCD Type 2 Lifecycle)
    # -------------------------------------------------------------------------
    with tabs[2]:
        render_section_header(
            "Trigger SCD Type 2 Career Progression / Promotion",
            "Invokes stored procedure sp_update_employee_scd2: closes prior version with effective_end_date and inserts a point-in-time new version in Dim_Employee."
        )

        emp_list = provider.get_all_employees(limit=50)
        emp_map = {e["employee_id"]: f"{e['full_name']} - {e.get('job_role', 'Role')} (${e.get('monthly_income', 0):,.0f})" for e in emp_list}

        sel_emp_id = st.selectbox(
            "Select Employee to Promote or Transfer:",
            options=list(emp_map.keys()),
            format_func=lambda x: emp_map.get(x, str(x)),
            key="scd2_promo_select",
        )

        current_emp = next((e for e in emp_list if e["employee_id"] == sel_emp_id), None)

        if current_emp:
            st.info(f"**Current Profile:** {current_emp['full_name']} | Dept: {current_emp.get('department_name', 'N/A')} | Role: {current_emp.get('job_role', 'N/A')} (Level {current_emp.get('job_level', 1)}) | Salary: ${current_emp.get('monthly_income', 0):,.2f}")

            with st.form("scd2_promotion_form"):
                p1, p2 = st.columns(2)
                with p1:
                    new_dept = st.selectbox("New Department:", [d["department_name"] for d in DEFAULT_DEPARTMENTS])
                    new_role = st.selectbox("New Job Role:", JOB_ROLES, index=min(2, len(JOB_ROLES)-1))
                    eff_date = st.date_input("Effective Transition Date:", value=date.today())
                with p2:
                    current_level = int(current_emp.get("job_level", 1))
                    new_level = st.selectbox("New Job Level:", [1, 2, 3, 4, 5], index=min(4, current_level))
                    cur_inc = float(current_emp.get("monthly_income", 5000.0))
                    new_salary = st.number_input(
                        "New Monthly Income ($):",
                        min_value=1000.0,
                        max_value=100000.0,
                        value=round(cur_inc * 1.15, 2),
                        step=250.0
                    )

                promo_submitted = st.form_submit_button("🚀 Execute SCD Type 2 Promotion", use_container_width=True)

                if promo_submitted:
                    try:
                        new_dept_id = dept_id_map.get(new_dept, 1)
                        success = provider.update_employee_scd2(
                            employee_id=sel_emp_id,
                            new_dept_id=new_dept_id,
                            new_role=new_role,
                            new_level=int(new_level),
                            new_salary=float(new_salary),
                            effective_date=eff_date,
                            attrition="No",
                        )
                        if success:
                            st.success(
                                f"✅ Successfully executed SCD Type 2 promotion for {current_emp['full_name']}! "
                                f"Prior record expired, new active version logged effective {eff_date} at ${new_salary:,.2f}."
                            )
                    except Exception as err:
                        st.error(f"SCD Type 2 progression failed: {err}")

    # -------------------------------------------------------------------------
    # TAB 4: Terminate / Attrition
    # -------------------------------------------------------------------------
    with tabs[3]:
        render_section_header("Workforce Separation / Attrition", "Soft-deletes employee by setting attrition='Yes' and updating warehouse status.")

        emp_list_active = [e for e in provider.get_all_employees(limit=50) if e.get("attrition") != "Yes"]
        active_map = {e["employee_id"]: f"{e['full_name']} ({e.get('job_role', '')})" for e in emp_list_active}

        if active_map:
            term_emp_id = st.selectbox(
                "Select Employee to Record Separation:",
                options=list(active_map.keys()),
                format_func=lambda x: active_map.get(x, str(x)),
                key="term_emp_select",
            )

            confirm = st.checkbox("⚠️ I confirm this separation record.")
            if st.button("Mark as Attrited", type="primary", disabled=not confirm):
                success = provider.terminate_employee(term_emp_id)
                if success:
                    st.warning(f"Employee #{term_emp_id} has been marked as Attrited.")
        else:
            st.info("No active employees available to terminate.")


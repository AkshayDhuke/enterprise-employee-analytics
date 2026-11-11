"""
Phase 4: Data Entry Module (OLTP Interaction & SCD Type 2)
Provides simple, intuitive web forms to:
1. Onboard new employees (inserts into OLTP & syncs to DW Dim_Employee)
2. Update an employee's department/role (specifically triggers SCD Type 2 in the Data Warehouse!)
3. Create new projects (inserts into OLTP)
4. Submit performance reviews (inserts into OLTP & syncs to DW Fact_PerformanceReviews)
"""

from datetime import date
import streamlit as st
import pandas as pd
from app.data_provider import DataProvider
from app.config import DEFAULT_DEPARTMENTS, JOB_ROLES


def render_data_entry_module(provider: DataProvider):
    st.title("📝 Data Entry & SCD Type 2 Management")
    st.caption("OLTP Transactional Operations & Automated SCD Type 2 Data Warehouse Synchronization")

    tabs = st.tabs([
        "➕ 1. Onboard New Employee",
        "🔄 2. Update Department (SCD Type 2)",
        "📁 3. Create Project",
        "⭐ 4. Submit Performance Review",
    ])

    # -------------------------------------------------------------------------
    # TAB 1: Onboard New Employee
    # -------------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Onboard New Employee (OLTP)")
        st.markdown("Creates a new record in `enterprise_oltp.employees` and synchronizes Version 1 into `enterprise_dw.Dim_Employee`.")

        with st.form("onboard_employee_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                first_name = st.text_input("First Name *", placeholder="e.g. John")
                last_name = st.text_input("Last Name *", placeholder="e.g. Doe")
                email = st.text_input("Corporate Email *", placeholder="john.doe@enterprise.com")
                gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
                age = st.number_input("Age", min_value=18, max_value=75, value=28)

            with col2:
                dept_names = [d["department_name"] for d in DEFAULT_DEPARTMENTS]
                dept_name = st.selectbox("Department *", dept_names)
                dept_id_map = {d["department_name"]: d["department_id"] for d in DEFAULT_DEPARTMENTS}
                dept_id = dept_id_map[dept_name]

                job_role = st.selectbox("Job Role *", JOB_ROLES)
                job_level = st.slider("Job Level (1 to 5)", min_value=1, max_value=5, value=1)
                monthly_income = st.number_input("Monthly Income ($) *", min_value=1000.0, max_value=50000.0, value=5500.0, step=250.0)
                hire_date = st.date_input("Hire Date", value=date.today())

            submitted = st.form_submit_button("✅ Onboard Employee", use_container_width=True)

            if submitted:
                if not first_name or not last_name or not email:
                    st.error("Please fill in all required fields (First Name, Last Name, Email).")
                else:
                    payload = {
                        "first_name": first_name.strip(),
                        "last_name": last_name.strip(),
                        "email": email.strip(),
                        "gender": gender,
                        "age": int(age),
                        "department_id": dept_id,
                        "job_role": job_role,
                        "job_level": job_level,
                        "monthly_income": float(monthly_income),
                        "education_field": "Computer Science",
                        "years_at_company": 0,
                        "attrition": "No",
                        "hire_date": str(hire_date),
                    }
                    new_id = provider.create_employee(payload)
                    st.success(f"🎉 Employee **{first_name} {last_name}** successfully onboarded! (Employee ID: `{new_id}`)")

    # -------------------------------------------------------------------------
    # TAB 2: Update Employee Department (Triggers SCD Type 2)
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Update Employee Department & Career Progression (SCD Type 2)")
        st.info(
            "💡 **SCD Type 2 Requirement:** When an employee transfers departments or gets promoted, "
            "the system **never overwrites** the old record. It retires the previous record (`is_current = 0`, "
            "`effective_end_date = NOW()`) and inserts a **new active version** (`is_current = 1`, `version = version + 1`)."
        )

        all_emps = provider.get_all_employees(limit=50)
        if all_emps:
            emp_map = {e["employee_id"]: f"{e['full_name']} (ID: {e['employee_id']} | Dept: {e['department_name']} | Role: {e['job_role']})" for e in all_emps}
            selected_emp_id = st.selectbox(
                "Select Employee to Update / Promote:",
                options=list(emp_map.keys()),
                format_func=lambda x: emp_map[x],
                key="scd2_select_emp",
            )

            # Find selected employee details
            current_emp = next((e for e in all_emps if e["employee_id"] == selected_emp_id), None)

            if current_emp:
                st.markdown("##### Current Employee State in Database:")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Current Department", current_emp["department_name"])
                c2.metric("Current Role", current_emp["job_role"])
                c3.metric("Current Job Level", f"Level {current_emp['job_level']}")
                c4.metric("Current Monthly Income", f"${current_emp['monthly_income']:,.2f}")

                st.divider()

                with st.form("scd2_update_form"):
                    st.markdown("##### New Department & Promotion Details:")
                    f_col1, f_col2 = st.columns(2)

                    with f_col1:
                        dept_names = [d["department_name"] for d in DEFAULT_DEPARTMENTS]
                        new_dept_name = st.selectbox("New Department *", dept_names, index=dept_names.index(current_emp["department_name"]) if current_emp["department_name"] in dept_names else 0)
                        dept_id_map = {d["department_name"]: d["department_id"] for d in DEFAULT_DEPARTMENTS}
                        new_dept_id = dept_id_map[new_dept_name]

                        new_role = st.selectbox("New Job Role *", JOB_ROLES, index=JOB_ROLES.index(current_emp["job_role"]) if current_emp["job_role"] in JOB_ROLES else 0)

                    with f_col2:
                        new_level = st.slider("New Job Level (1 to 5)", min_value=1, max_value=5, value=min(current_emp["job_level"] + 1, 5))
                        new_salary = st.number_input(
                            "New Monthly Income ($) *",
                            min_value=1000.0,
                            max_value=60000.0,
                            value=float(current_emp["monthly_income"]) * 1.15,
                            step=500.0,
                        )

                    update_btn = st.form_submit_button("🚀 Apply Transfer / Promotion (Trigger SCD Type 2)", use_container_width=True)

                    if update_btn:
                        success = provider.update_employee_scd2(
                            employee_id=selected_emp_id,
                            new_department_id=new_dept_id,
                            new_role=new_role,
                            new_salary=float(new_salary),
                            new_level=new_level,
                            promotion_date=str(date.today()),
                        )
                        if success:
                            st.success(f"✨ Successfully triggered SCD Type 2 update! Department set to **{new_dept_name}** at **${new_salary:,.2f}/mo**.")

                # Show SCD Type 2 Audit Trail Table
                st.markdown("##### SCD Type 2 Historical Audit Trail for this Employee:")
                scd2_df = provider.get_scd2_audit_trail(employee_id=selected_emp_id)
                if not scd2_df.empty:
                    st.dataframe(scd2_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("No historical versions recorded yet.")
        else:
            st.warning("No employees available to update.")

    # -------------------------------------------------------------------------
    # TAB 3: Create Project
    # -------------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Create Project (OLTP)")
        st.markdown("Creates a new project record in `enterprise_oltp.projects`.")

        with st.form("create_project_form", clear_on_submit=True):
            p1, p2 = st.columns(2)
            with p1:
                proj_code = st.text_input("Project Code *", placeholder="e.g. PRJ-2026-CLOUD")
                proj_name = st.text_input("Project Name *", placeholder="e.g. Cloud Data Lake Migration")
                dept_names = [d["department_name"] for d in DEFAULT_DEPARTMENTS]
                proj_dept = st.selectbox("Assigned Department *", dept_names, key="proj_dept")
                dept_id = {d["department_name"]: d["department_id"] for d in DEFAULT_DEPARTMENTS}[proj_dept]
                priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"])

            with p2:
                status = st.selectbox("Project Status", ["Active", "Planning", "On Hold", "Completed"])
                budget = st.number_input("Allocated Budget ($)", min_value=5000.0, max_value=5000000.0, value=75000.0, step=5000.0)
                start_date = st.date_input("Start Date", value=date.today())
                end_date = st.date_input("Estimated End Date", value=date.today().replace(year=date.today().year + 1))

            proj_btn = st.form_submit_button("📁 Create Project", use_container_width=True)
            if proj_btn:
                if not proj_code or not proj_name:
                    st.error("Please provide both Project Code and Project Name.")
                else:
                    payload = {
                        "project_code": proj_code.strip(),
                        "project_name": proj_name.strip(),
                        "department_id": dept_id,
                        "priority": priority,
                        "status": status,
                        "budget": float(budget),
                        "start_date": str(start_date),
                        "end_date": str(end_date),
                    }
                    new_proj_id = provider.create_project(payload)
                    st.success(f"🎉 Project **{proj_name}** (`{proj_code}`) created successfully! (Project ID: `{new_proj_id}`)")

    # -------------------------------------------------------------------------
    # TAB 4: Submit Performance Review
    # -------------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Submit Performance Review (OLTP & DW Sync)")
        st.markdown("Submits an evaluation into `enterprise_oltp.performance_reviews` and synchronizes to `Fact_PerformanceReviews`.")

        all_emps = provider.get_all_employees(limit=50)
        if all_emps:
            with st.form("submit_review_form", clear_on_submit=True):
                r1, r2 = st.columns(2)
                with r1:
                    rev_emp_map = {e["employee_id"]: f"{e['full_name']} ({e['job_role']})" for e in all_emps}
                    rev_emp_id = st.selectbox(
                        "Select Employee *",
                        options=list(rev_emp_map.keys()),
                        format_func=lambda x: rev_emp_map[x],
                    )
                    review_cycle = st.selectbox("Review Cycle *", ["2026-Annual", "2026-Q4", "2026-Q3", "2026-MidYear"])
                    review_date = st.date_input("Review Date", value=date.today())

                with r2:
                    perf_rating = st.slider("Performance Rating (1 = Unsatisfactory, 5 = Outstanding) *", min_value=1, max_value=5, value=4)
                    work_life = st.slider("Work-Life Balance (1 to 4)", min_value=1, max_value=4, value=3)
                    job_sat = st.slider("Job Satisfaction (1 to 4)", min_value=1, max_value=4, value=3)
                    training_times = st.number_input("Training Hours / Sessions Last Year", min_value=0, max_value=50, value=4)

                reviewer_notes = st.text_area("Reviewer Comments & Feedback", placeholder="Consistently exceeds departmental expectations and demonstrates strong teamwork...")

                rev_btn = st.form_submit_button("⭐ Submit Performance Review", use_container_width=True)
                if rev_btn:
                    payload = {
                        "employee_id": rev_emp_id,
                        "review_date": str(review_date),
                        "review_cycle": review_cycle,
                        "performance_rating": perf_rating,
                        "work_life_balance": work_life,
                        "job_satisfaction": job_sat,
                        "training_times_last_year": int(training_times),
                        "reviewer_comments": reviewer_notes.strip(),
                    }
                    new_rev_id = provider.submit_review(payload)
                    st.success(f"🎉 Performance Review successfully recorded for Employee #{rev_emp_id}! (Review ID: `{new_rev_id}`)")
        else:
            st.warning("No employees found to review.")

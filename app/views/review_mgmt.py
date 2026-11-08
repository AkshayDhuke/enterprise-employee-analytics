"""
Performance Review Evaluation View.
Enables managers to record employee evaluations and sync point-in-time facts into Fact_PerformanceReviews.
"""

from datetime import date
import streamlit as st
import pandas as pd

from app.data_provider import DataProvider
from app.utils.ui_helpers import render_section_header


def render_review_mgmt_view(provider: DataProvider):
    """Renders the performance review submission and history view."""
    st.title("⭐ Performance Review & Fact Synchronization")
    st.markdown("Records periodic employee reviews and synchronizes point-in-time fact metrics with the Star Schema warehouse.")

    tabs = st.tabs(["📝 Submit Review", "📚 Review History"])

    # -------------------------------------------------------------------------
    # TAB 1: Submit Review
    # -------------------------------------------------------------------------
    with tabs[0]:
        render_section_header(
            "Record Employee Performance Evaluation",
            "Creates transactional entry in enterprise_oltp.performance_reviews and joins point-in-time SCD2 employee_sk to load Fact_PerformanceReviews."
        )

        employees = provider.get_all_employees(limit=50)
        if employees:
            emp_options = {e["employee_id"]: f"{e['full_name']} - {e.get('job_role', '')}" for e in employees}

            with st.form("submit_review_form", clear_on_submit=True):
                e_id = st.selectbox(
                    "Employee Under Evaluation *",
                    options=list(emp_options.keys()),
                    format_func=lambda x: emp_options[x],
                )

                col1, col2 = st.columns(2)
                with col1:
                    review_date = st.date_input("Evaluation Date *", value=date.today())
                    review_cycle = st.selectbox("Evaluation Cycle *", ["Annual Review", "Mid-Year Review", "Q1 Review", "Q2 Review", "Q3 Review", "Q4 Review"])
                    perf_rating = st.slider("Performance Rating (1=Low, 5=Exemplary) *", min_value=1.0, max_value=5.0, value=4.0, step=0.1)
                with col2:
                    satisfaction = st.select_slider("Job Satisfaction (1-5)", options=[1, 2, 3, 4, 5], value=4)
                    wlb = st.select_slider("Work-Life Balance (1-5)", options=[1, 2, 3, 4, 5], value=3)
                    training_times = st.number_input("Training Hours / Sessions Last Year", min_value=0, max_value=20, value=3)

                comments = st.text_area("Reviewer Feedback & Development Goals", placeholder="Demonstrated strong technical leadership and cross-functional collaboration...")

                submit_btn = st.form_submit_button("⭐ Submit & Synchronize to DW", use_container_width=True)

                if submit_btn:
                    rev_payload = {
                        "employee_id": e_id,
                        "review_date": str(review_date),
                        "review_cycle": review_cycle,
                        "performance_rating": float(perf_rating),
                        "job_satisfaction": int(satisfaction),
                        "work_life_balance": int(wlb),
                        "training_times_last_year": int(training_times),
                        "reviewer_comments": comments.strip(),
                    }
                    try:
                        rev_id = provider.submit_review(rev_payload)
                        st.success(
                            f"🎉 Review #{rev_id} for {emp_options[e_id]} successfully logged! "
                            f"Point-in-time snapshot committed to Fact_PerformanceReviews in enterprise_dw."
                        )
                    except Exception as ex:
                        st.error(f"Failed to submit review: {ex}")
        else:
            st.info("No active employees found to evaluate.")

    # -------------------------------------------------------------------------
    # TAB 2: Review History
    # -------------------------------------------------------------------------
    with tabs[1]:
        render_section_header("Historical Performance Records")
        reviews_df = provider._demo_reviews_df.copy()
        if not reviews_df.empty:
            reviews_df["monthly_income"] = reviews_df["monthly_income"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            cols = ["full_name", "department_name", "job_role", "year_num", "performance_rating", "job_satisfaction", "monthly_income"]
            df_disp = reviews_df[cols].copy()
            df_disp.columns = ["Employee", "Department", "Role", "Year", "Rating", "Satisfaction", "Monthly Salary"]
            st.dataframe(df_disp, use_container_width=True, hide_index=True)
        else:
            st.info("No historical reviews recorded.")


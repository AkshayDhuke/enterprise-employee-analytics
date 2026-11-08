"""
Database Administration & Warehouse Diagnostics View.
Displays connection status, connection pool configurations, stored procedure manifests,
and an interactive SQL console.
"""

import time
import streamlit as st
import pandas as pd

from app.data_provider import DataProvider
from app.utils.ui_helpers import render_section_header


def render_database_admin_view(provider: DataProvider):
    """Renders the database administration and health dashboard."""
    st.title("🛠️ Data Warehouse Health & Admin Console")
    st.markdown("Monitor connection pools, verify ETL stored procedures, and inspect schemas across OLTP and Data Warehouse.")

    tabs = st.tabs(["🔌 Connection Diagnostics", "🏛️ Architecture & Stored Procedures", "💻 SQL Query Console"])

    # -------------------------------------------------------------------------
    # TAB 1: Connection Diagnostics
    # -------------------------------------------------------------------------
    with tabs[0]:
        render_section_header("Database Connectivity & Connection Pools")

        status = provider.db.test_connections()
        c1, c2 = st.columns(2)
        with c1:
            if status["oltp"]:
                st.success("🟢 enterprise_oltp: CONNECTED")
            else:
                st.error("🔴 enterprise_oltp: DISCONNECTED")
                if "oltp" in status.get("errors", {}):
                    st.caption(f"Error: {status['errors']['oltp']}")

        with c2:
            if status["dw"]:
                st.success("🟢 enterprise_dw: CONNECTED")
            else:
                st.error("🔴 enterprise_dw: DISCONNECTED")
                if "dw" in status.get("errors", {}):
                    st.caption(f"Error: {status['errors']['dw']}")

        st.divider()

        render_section_header("Configure Database Credentials")
        st.markdown("Update your MySQL connection parameters to connect directly to your local MySQL instance:")

        with st.form("db_reconnect_form"):
            col_h, col_p = st.columns(2)
            with col_h:
                host = st.text_input("MySQL Host", value=provider.db.host)
                user = st.text_input("Database User", value=provider.db.user)
            with col_p:
                port = st.text_input("Port", value=str(provider.db.port))
                pwd = st.text_input("Password", type="password", value=provider.db.password)

            btn_test = st.form_submit_button("🔄 Reconnect & Test Database Pools", use_container_width=True)

            if btn_test:
                with st.spinner("Probing database connection pools..."):
                    res = provider.reconnect(user=user, password=pwd, host=host, port=port)
                    if res["oltp"] and res["dw"]:
                        st.success("🎉 Successfully connected to both enterprise_oltp and enterprise_dw!")
                        st.rerun()
                    else:
                        st.error("Failed to connect to one or both databases. Check credentials or ensure MySQL server is running.")
                        st.json(res.get("errors", {}))

    # -------------------------------------------------------------------------
    # TAB 2: Architecture & Stored Procedures
    # -------------------------------------------------------------------------
    with tabs[1]:
        render_section_header("ETL Stored Procedures & Pipeline Architecture")

        st.markdown(
            """
            The data warehouse architecture consists of two distinct MySQL schemas:
            1. **enterprise_oltp (3NF Normalized)**: High-concurrency transactional store (`departments`, `employees`, `projects`, `project_assignments`, `performance_reviews`).
            2. **enterprise_dw (Star Schema with SCD Type 2)**: Analytical warehouse (`Dim_Date`, `Dim_Department`, `Dim_Project`, `Dim_Employee` [SCD2], `Fact_PerformanceReviews`, `Fact_ProjectAllocations`).
            """
        )

        st.markdown("### Stored Procedures Manifest (Phase 2):")
        procs = [
            {"Procedure": "sp_populate_dim_date(start_year, end_year)", "Schema": "enterprise_dw", "Description": "Generates 10+ years of calendar dimension data with quarters, day names, and weekend flags."},
            {"Procedure": "sp_etl_staging_to_oltp()", "Schema": "enterprise_staging", "Description": "Normalizes flat 100k+ staging records into 3NF OLTP tables using CTEs and ROW_NUMBER() ranking."},
            {"Procedure": "sp_etl_load_dimensions()", "Schema": "enterprise_dw", "Description": "Performs initial load of Dim_Department, Dim_Project, and Dim_Employee from OLTP into DW."},
            {"Procedure": "sp_update_employee_scd2(...)", "Schema": "enterprise_dw", "Description": "Atomic SCD Type 2 stored procedure: expires previous version (effective_end_date = NOW) and inserts version + 1."},
            {"Procedure": "sp_etl_load_fact_performance()", "Schema": "enterprise_dw", "Description": "Populates Fact_PerformanceReviews with point-in-time surrogate key alignment."},
            {"Procedure": "sp_etl_load_fact_allocations()", "Schema": "enterprise_dw", "Description": "Populates Fact_ProjectAllocations for bottleneck workload tracking."},
        ]
        st.dataframe(pd.DataFrame(procs), use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # TAB 3: SQL Query Console
    # -------------------------------------------------------------------------
    with tabs[2]:
        render_section_header("Interactive SQL Query Console")
        st.caption("Execute custom read queries against enterprise_oltp or enterprise_dw.")

        target_db = st.radio("Target Schema:", ["enterprise_dw (Data Warehouse)", "enterprise_oltp (Transactional OLTP)"], horizontal=True)
        use_dw = "dw" in target_db.lower()

        default_query = "SELECT * FROM Dim_Employee WHERE is_current = 1 LIMIT 10;" if use_dw else "SELECT * FROM employees LIMIT 10;"
        query_text = st.text_area("SQL Statement:", value=default_query, height=120)

        if st.button("▶ Run Query", type="primary"):
            if not provider.is_live:
                st.warning("⚠️ Database is currently in Demonstration Mode (offline). Live queries require a connected MySQL instance.")
            else:
                try:
                    start_t = time.time()
                    results = provider.analytics_dal.execute_query(query_text, use_dw=use_dw)
                    dur = (time.time() - start_t) * 1000
                    st.success(f"Execution complete: {len(results)} row(s) returned in {dur:.1f}ms.")
                    if results:
                        st.dataframe(pd.DataFrame(results), use_container_width=True)
                    else:
                        st.info("Query returned 0 rows.")
                except Exception as ex:
                    st.error(f"SQL Execution Error: {ex}")

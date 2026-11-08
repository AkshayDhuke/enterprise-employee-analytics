"""
UI Helper utilities and styling components for Streamlit application.
Provides polished enterprise design elements, custom metrics, and status badges.
"""

import streamlit as st


def apply_custom_css():
    """Injects modern, corporate-grade CSS for cards, metrics, and navigation."""
    st.markdown(
        """
        <style>
        /* General App Styling */
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 95%;
        }

        /* Metric Cards */
        .metric-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 18px 22px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -2px rgba(0, 0, 0, 0.2);
            color: #f8fafc;
            margin-bottom: 15px;
            transition: transform 0.15s ease-in-out;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: #38bdf8;
        }
        .metric-title {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 1.85rem;
            font-weight: 700;
            color: #f1f5f9;
            line-height: 1.2;
        }
        .metric-delta {
            font-size: 0.8rem;
            margin-top: 6px;
            font-weight: 500;
        }
        .delta-positive { color: #34d399; }
        .delta-negative { color: #f87171; }
        .delta-neutral { color: #94a3b8; }

        /* Section Header */
        .section-header {
            border-left: 4px solid #38bdf8;
            padding-left: 12px;
            margin: 20px 0 15px 0;
            font-size: 1.25rem;
            font-weight: 600;
            color: #e2e8f0;
        }

        /* Custom Status Badges */
        .badge {
            display: inline-block;
            padding: 3px 10px;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 9999px;
            text-transform: uppercase;
        }
        .badge-success { background-color: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid #34d399; }
        .badge-danger { background-color: rgba(248, 113, 113, 0.15); color: #f87171; border: 1px solid #f87171; }
        .badge-warning { background-color: rgba(251, 191, 36, 0.15); color: #fbbf24; border: 1px solid #fbbf24; }
        .badge-info { background-color: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #38bdf8; }

        /* SQL Query Code Container */
        .sql-box {
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.85rem;
            color: #79c0ff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(
    title: str,
    value: str,
    delta: str = None,
    delta_type: str = "neutral",
    icon: str = "📊",
):
    """Renders a styled KPI metric card component."""
    delta_class = f"delta-{delta_type}"
    delta_html = f'<div class="metric-delta {delta_class}">{delta}</div>' if delta else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">{icon} {title}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str = ""):
    """Renders a standard section header with an optional subtitle."""
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)


"""Reusable UI components for the AI CV Advisory Board application."""

import streamlit as st

STEPS = [
    {"label": "Setup"},
    {"label": "Upload"},
    {"label": "Job"},
    {"label": "Team"},
    {"label": "Results"},
    {"label": "Polish"},
]


def render_stepper(current_step):
    """Render a step-by-step progress indicator.

    Args:
        current_step: The current step number (1-indexed).
    """
    cols = st.columns(len(STEPS))
    for i, (col, step) in enumerate(zip(cols, STEPS)):
        step_num = i + 1
        with col:
            if current_step == step_num:
                st.markdown(f"**🔷 {step['label']}**")
                st.progress(100)
            elif current_step > step_num:
                st.markdown(f"**✅ {step['label']}**")
                st.progress(100)
            else:
                st.markdown(f"<span style='color: #888;'>⚪ {step['label']}</span>", unsafe_allow_html=True)
                st.progress(0)
    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)


def render_demo_lock(feature: str):
    """Standard lock notice for features excluded from demo mode."""
    st.info(
        f"🔒 **{feature}** is available in the full version - exit the demo and bring your own API key (or a local Ollama)."
    )


def render_demo_banner():
    """Demo-mode banner with an exit button. Returns True if the user exited."""
    col_text, col_btn = st.columns([4, 1])
    col_text.info("🎮 **Demo mode** - fixed sample CV and job posting.")
    return col_btn.button("Exit demo", use_container_width=True)


def render_header():
    """Render the application header."""
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>AI - CV Advisory Board</h1>", unsafe_allow_html=True)


def render_footer():
    """Render the application footer."""
    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="text-align: center; font-size: 0.7rem; color: #888; margin-bottom: 5px;">
            Author: <a href="https://linkedin.com/in/carlosan1708" target="_blank">linkedin/carlosan1708</a><br>
            🔒 CVs are processed in memory and never logged. Analysis history is stored locally only.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Buy Me a Coffee Button - Direct Link (Mobile Friendly)
    st.markdown(
        """
        <div style="text-align: center; margin-top: 20px;">
            <a href="https://www.buymeacoffee.com/carlosan1708" target="_blank" style="text-decoration: none;">
                <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 40px; width: auto;">
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

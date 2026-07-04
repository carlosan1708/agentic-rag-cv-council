"""Module for rendering the CV upload step in the application."""

import streamlit as st

from services.cv_service import CVService
from state_manager import state_manager


def render_upload_step():
    """Render the CV upload step UI."""
    st.subheader("Step 2: Upload Your CV")

    st.caption(
        "🔒 Your CV is processed in memory and sent only to the AI provider you configured. "
        "It is never logged or stored on the server."
    )

    with st.container(border=True):
        uploaded_file = st.file_uploader("Upload PDF, DOCX or TXT", type=["pdf", "docx", "txt"])

        if uploaded_file:
            # Check file size (e.g., limit to 5MB)
            if uploaded_file.size > 5 * 1024 * 1024:
                st.error("File is too large. Please upload a file smaller than 5MB.")
                return

            if uploaded_file.name != st.session_state.cv_filename:
                with st.spinner("Reading file..."):
                    try:
                        content = CVService.parse_cv_file(uploaded_file.read(), uploaded_file.name)
                        st.session_state.cv_content = content
                        st.session_state.cv_filename = uploaded_file.name
                    except Exception as e:
                        st.error(f"Error reading file: {str(e)}")

            if st.session_state.cv_content:
                st.success(f"✅ Successfully loaded: **{st.session_state.cv_filename}**")
                st.markdown(f"**Preview:** {st.session_state.cv_content[:150]}...")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            state_manager.prev_step()
    with col2:
        disabled = not st.session_state.cv_content
        if st.button("Next: Job Target ➡️", type="primary", disabled=disabled, use_container_width=True):
            state_manager.next_step()

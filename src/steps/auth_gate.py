"""Access gate shown when AUTH_MODE=approval and the visitor is not logged in."""

import streamlit as st

from services.auth_service import STATUS_APPROVED, AuthService, admin_code, auth_enabled, valid_email


def gate_required() -> bool:
    """True when the gate must be shown instead of the app."""
    if not auth_enabled():
        return False
    if st.session_state.get("auth_user"):
        return False
    if st.session_state.get("demo_mode"):
        return False
    return True


def _render_login_tab():
    st.markdown("Enter the email and access code from your approved request.")
    email = st.text_input("Email", key="login_email")
    code = st.text_input("Access code", key="login_code", type="password")
    if st.button("🔓 Login", type="primary", use_container_width=True):
        status = AuthService.login(email, code)
        if status == STATUS_APPROVED:
            st.session_state.auth_user = email.strip().lower()
            st.rerun()
        elif status is not None:
            st.warning("⏳ Your request is still pending approval. Please check back later.")
        else:
            st.error("Invalid email or access code.")


def _render_request_tab():
    st.markdown(
        "Access to this deployment is granted manually. Request access below and **save your "
        "access code** - you'll use it to log in once your request is approved."
    )
    email = st.text_input("Your email", key="request_email")
    if st.button("✉️ Request Access", type="primary", use_container_width=True):
        if not valid_email(email):
            st.error("Please enter a valid email address.")
            return
        code = AuthService.request_access(email)
        if code:
            st.success("Request registered! Save your access code now - it is only shown here:")
            st.code(code)
            st.caption("Once the admin approves your request, log in with your email and this code.")
        else:
            st.error("Could not register the request. Please try again later.")


def _render_admin_tab():
    configured_code = admin_code()
    if not configured_code:
        st.info("Admin panel disabled: set the ADMIN_CODE environment variable to enable it.")
        return

    entered = st.text_input("Admin code", type="password", key="admin_code_input")
    if entered != configured_code:
        if entered:
            st.error("Wrong admin code.")
        return

    pending = AuthService.list_pending()
    st.markdown(f"**Pending requests ({len(pending)}):**")
    if not pending:
        st.caption("No pending requests.")
    for user in pending:
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.write(f"📧 {user.email} · {user.created_at}")
        if col2.button("✅ Approve", key=f"approve_{user.email}"):
            AuthService.approve(user.email)
            st.rerun()
        if col3.button("❌ Reject", key=f"reject_{user.email}"):
            AuthService.reject(user.email)
            st.rerun()

    approved = [u for u in AuthService.list_users() if u.status == STATUS_APPROVED]
    if approved:
        with st.expander(f"Approved users ({len(approved)})"):
            for user in approved:
                col1, col2 = st.columns([4, 1])
                col1.write(f"✅ {user.email} · {user.created_at}")
                if col2.button("🗑️ Revoke", key=f"revoke_{user.email}"):
                    AuthService.reject(user.email)
                    st.rerun()


def render_auth_gate():
    """Renders the login/request/admin gate. Call st.stop() after this."""
    st.markdown(
        """
        <div style="text-align: center; padding-top: 5px;">
            <h2 style="margin-top: 5px; margin-bottom: 0;">🔐 Private Beta</h2>
            <p style="font-size: 1rem; color: #555;">
                This deployment requires an approved account.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["🔓 Login", "✉️ Request Access", "🛡️ Admin"])
    with tabs[0]:
        _render_login_tab()
    with tabs[1]:
        _render_request_tab()
    with tabs[2]:
        _render_admin_tab()

    st.write("---")
    st.markdown("**No account?** Explore the product with sample data:")
    if st.button("🎮 Try the Demo", use_container_width=True):
        from steps.welcome import start_demo

        start_demo()

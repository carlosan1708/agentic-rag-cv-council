"""Module for rendering the team selection step in the application."""

import streamlit as st
import yaml

from services.persona_service import PersonaService
from state_manager import state_manager


def _handle_custom_specialist():
    """Handle creating custom specialist personas (persona builder)."""
    with st.expander("➕ Persona Builder: Add a Custom Specialist", expanded=False):
        custom_name = st.text_input("Specialist Name (e.g., 'Google Senior Engineer')")
        custom_role = st.text_input(
            "Role (optional)",
            placeholder="e.g., 'Staff Engineer interviewer at a FAANG company'",
        )
        custom_goal = st.text_input(
            "Goal (optional)",
            placeholder="e.g., 'Evaluate system design depth and seniority signals'",
        )
        custom_backstory = st.text_area(
            "Backstory / focus",
            help="Describe the persona's background and what they should look for in the CV.",
        )
        if st.button("Add to Board"):
            if custom_name and custom_backstory:
                new_agent = {
                    "name": custom_name,
                    "role": custom_role or custom_name,
                    "goal": custom_goal or f"Provide specialized analysis as {custom_name}",
                    "backstory": custom_backstory,
                }
                state_manager.custom_agents.append(new_agent)
                st.success(f"Added {custom_name} to the board!")
                st.rerun()
            else:
                st.warning("A name and a backstory are required.")


def _render_custom_agents():
    """Lists custom specialists with delete buttons and a YAML export."""
    if not state_manager.custom_agents:
        return

    st.subheader("Your Custom Specialists")
    for idx, agent in enumerate(state_manager.custom_agents):
        col1, col2 = st.columns([4, 1])
        col1.write(f"👤 **{agent['name']}**")
        if col2.button("🗑️", key=f"del_{idx}"):
            state_manager.custom_agents.pop(idx)
            st.rerun()

    yaml_export = yaml.safe_dump(state_manager.custom_agents, sort_keys=False, allow_unicode=True)
    st.download_button(
        "⬇️ Export custom personas as YAML",
        data=yaml_export,
        file_name="custom_personas.yaml",
        mime="text/yaml",
        help="Drop the file into the 'personas/' directory (or contribute it!) to reuse these specialists.",
    )


def render_team_step():
    """Render the team selection step UI."""
    st.subheader("Step 4: Assemble Your Board")

    # Load personas using PersonaService
    available_personas = PersonaService.load_personas()

    if not available_personas:
        st.error("No personas found. Please check the 'personas' directory.")
        return

    st.info("💡 **Note:** To manage API costs and ensure efficient processing, please select a **maximum of 3 specialists**.")

    # Create a container for the checkboxes
    current_selection = state_manager.selected_persona_names
    new_selection = []

    with st.container():
        for name, persona in available_personas.items():
            # Check if this persona is currently in the selected list
            is_selected = name in current_selection

            # Disable unchecked boxes if we already have 3 selected
            is_disabled = len(current_selection) >= 3 and not is_selected

            checked = st.checkbox(
                f"**{name}**",
                value=is_selected,
                key=f"chk_{name}",
                help=persona.backstory,
                disabled=is_disabled,
            )

            if checked:
                new_selection.append(name)

    # Safety check (though disabled logic should prevent this)
    if len(new_selection) > 3:
        st.warning("⚠️ You can only select up to 3 specialists. Truncating selection.")
        new_selection = new_selection[:3]

    # Update state_manager with the new selection list
    state_manager.selected_persona_names = new_selection

    # Map selected names back to Persona objects for the board
    selected_personas = [available_personas[name] for name in new_selection]
    st.session_state.board_agents = selected_personas

    _handle_custom_specialist()
    _render_custom_agents()

    st.toggle(
        "🗣️ Debate round (Devil's Advocate)",
        key="debate_mode",
        help="Adds an extra agent that challenges the specialists' findings before the final synthesis. "
        "Improves rigor, costs extra tokens.",
    )

    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            state_manager.prev_step()
    with col2:
        # Require at least one specialist (either pre-defined or custom)
        is_ready = len(new_selection) > 0 or len(state_manager.custom_agents) > 0
        if st.button("Next: Run Analysis ➡️", type="primary", disabled=not is_ready, use_container_width=True):
            state_manager.next_step()

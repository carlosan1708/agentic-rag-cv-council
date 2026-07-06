"""Module for rendering the system configuration step in the application."""

import streamlit as st

from services.config_service import PROVIDERS, ConfigService
from state_manager import state_manager


def on_provider_change():
    """Callback when provider changes."""
    is_online = state_manager.config.is_online
    new_provider = st.session_state.online_provider_select if is_online else st.session_state.offline_provider_select

    if new_provider != state_manager.config.llm_provider:
        api_key = ""
        if not is_online:
            api_key = ConfigService.get_env_api_key(new_provider)

        state_manager.update_config(
            llm_provider=new_provider, api_key=api_key, selected_model=ConfigService.get_cheap_model(new_provider)
        )

        if "available_models" in st.session_state:
            del st.session_state.available_models


def on_api_key_change():
    """Callback when API key input changes."""
    is_online = state_manager.config.is_online
    key_widget = "online_api_key_input" if is_online else "offline_api_key_input"
    new_key = st.session_state.get(key_widget, "")

    if new_key != state_manager.config.api_key:
        if is_online and not new_key:
            new_key = ConfigService.get_env_api_key(state_manager.config.llm_provider)

        state_manager.update_config(api_key=new_key)

        if "available_models" in st.session_state:
            del st.session_state.available_models


def on_model_change():
    """Callback when model selection changes."""
    state_manager.update_config(selected_model=st.session_state.model_selector)


def _provider_index(provider: str) -> int:
    return PROVIDERS.index(provider) if provider in PROVIDERS else 0


def _render_key_input(config, widget_key: str, is_online: bool):
    """Renders the API key input, unless the provider is keyless (e.g. Ollama)."""
    if not ConfigService.requires_api_key(config.llm_provider):
        st.info("🖥️ Ollama runs locally - no API key required. Make sure the Ollama server is running.")
        return

    current_val = config.api_key
    if is_online:
        system_key = ConfigService.get_env_api_key(config.llm_provider)
        if current_val == system_key:
            current_val = ""
        help_text = "Leave empty to use the system's default key."
    else:
        help_text = f"Required to access {config.llm_provider} models."

    st.text_input(
        f"Enter your {config.llm_provider} API Key",
        type="password",
        value=current_val,
        help=help_text,
        key=widget_key,
        on_change=on_api_key_change,
    )


def _render_online_config(config):
    """Render configuration for online mode."""
    st.success(f"System is pre-configured with **{config.selected_model}** and ready to go!")
    with st.expander("🛠️ Advanced: Change Provider / Custom API Key", expanded=False):
        st.radio(
            "Select AI Provider",
            options=PROVIDERS,
            horizontal=True,
            index=_provider_index(config.llm_provider),
            key="online_provider_select",
            on_change=on_provider_change,
        )
        _render_key_input(config, "online_api_key_input", is_online=True)


def _render_offline_config(config):
    """Render configuration for offline mode."""
    st.info("Let's get your AI environment set up first.")
    with st.container(border=True):
        st.radio(
            "Select AI Provider",
            options=PROVIDERS,
            horizontal=True,
            index=_provider_index(config.llm_provider),
            key="offline_provider_select",
            on_change=on_provider_change,
        )
        _render_key_input(config, "offline_api_key_input", is_online=False)


def _get_available_models(config, is_online):
    """Fetch available models based on current config."""
    active_key = config.api_key
    system_key = ConfigService.get_env_api_key(config.llm_provider)

    custom_key_widget = "online_api_key_input" if is_online else "offline_api_key_input"
    custom_key_input = st.session_state.get(custom_key_widget, "")

    if is_online and not custom_key_input:
        active_key = system_key

    keyless = not ConfigService.requires_api_key(config.llm_provider)
    available_models = []
    if active_key or keyless:
        cache_key = f"models_{config.llm_provider}_{active_key}"
        if cache_key in st.session_state:
            available_models = st.session_state[cache_key]
        else:
            available_models = ConfigService.fetch_models(config.llm_provider, active_key)
            if available_models:
                st.session_state[cache_key] = available_models
    return available_models, custom_key_input, system_key


def _render_model_selection(config, available_models, custom_key_input, system_key):
    """Render model selection dropdown."""
    if available_models:
        if ConfigService.requires_api_key(config.llm_provider):
            st.success(f"{config.llm_provider} API Key Validated!")
        else:
            st.success(f"Connected to local {config.llm_provider} server!")

        current_selection = config.selected_model
        if current_selection not in available_models:
            current_selection = ConfigService.get_cheap_model(config.llm_provider)
            if current_selection not in available_models:
                current_selection = available_models[0]
            state_manager.update_config(selected_model=current_selection)

        default_index = available_models.index(current_selection)
        has_custom_key = bool(custom_key_input) and custom_key_input != system_key
        lock_it = config.is_online and not has_custom_key and ConfigService.requires_api_key(config.llm_provider)

        st.selectbox(
            f"Select {config.llm_provider} Model",
            options=available_models,
            index=default_index,
            key="model_selector",
            on_change=on_model_change,
            disabled=lock_it,
        )
        if lock_it:
            st.info(
                "💡 Note: The selected model is efficient but not the most powerful, as this service "
                "is self-financed. To use more advanced models, please provide your own API key above."
            )
    elif not ConfigService.requires_api_key(config.llm_provider):
        st.error("Could not reach the local Ollama server. Is it running? (Set OLLAMA_BASE_URL if not on localhost.)")
    elif config.api_key:
        st.error("Invalid API Key or no models available.")


def render_config_step():
    """Render the configuration step UI."""
    st.subheader("Step 1: System Configuration")

    config = state_manager.config
    if config.is_online:
        _render_online_config(config)
    else:
        _render_offline_config(config)

    models, custom_key, sys_key = _get_available_models(config, config.is_online)
    _render_model_selection(config, models, custom_key, sys_key)

    if st.button("Next: Upload CV ➡️", type="primary", disabled=not models, use_container_width=True):
        state_manager.next_step()

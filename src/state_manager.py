import uuid

import streamlit as st

from models import AppConfig, JobInfo
from services.config_service import ConfigService


class StateManager:
    """Manages the application state, abstracting Streamlit's session_state."""

    def __init__(self):
        # We don't initialize here because st.session_state is not always available
        # when the module is first imported as a singleton.
        pass

    def ensure_initialized(self):
        """Ensures that all required session state variables are initialized."""
        is_online = ConfigService.get_is_online()
        config = AppConfig(
            is_online=is_online,
            llm_provider="Google",
            api_key=ConfigService.get_env_api_key("Google") if is_online else "",
            selected_model=ConfigService.get_cheap_model("Google") if is_online else "",
        )

        defaults = {
            "step": 0,
            "config": config,
            "job": JobInfo(),
            "cv_content": "",
            "cv_filename": "",
            "selected_persona_names": ["LinkedIn Matchmaker (matchmaker)"],
            "custom_agents": [],
            "crew_result": None,
            "interview_questions": [],
            "user_answers": {},
            "interview_done": False,
            "board_agents": [],
            "generate_cover_letter": False,
            "debate_mode": False,
            "interview_prep": "",
            "token_usage": None,
            "history_saved": False,
            "compare_jobs": [],
            "history_owner": None,
            "demo_mode": False,
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

        if st.session_state.history_owner is None:
            from services.history_service import DEFAULT_OWNER, session_scoped

            st.session_state.history_owner = uuid.uuid4().hex if session_scoped() else DEFAULT_OWNER

    @property
    def step(self) -> int:
        self.ensure_initialized()
        return st.session_state.step

    @step.setter
    def step(self, value: int):
        self.ensure_initialized()
        st.session_state.step = value

    @property
    def config(self) -> AppConfig:
        self.ensure_initialized()
        return st.session_state.config

    @property
    def job(self) -> JobInfo:
        self.ensure_initialized()
        return st.session_state.job

    @property
    def custom_agents(self) -> list:
        self.ensure_initialized()
        return st.session_state.custom_agents

    @property
    def selected_persona_names(self) -> list:
        self.ensure_initialized()
        return st.session_state.selected_persona_names

    @selected_persona_names.setter
    def selected_persona_names(self, value: list):
        self.ensure_initialized()
        st.session_state.selected_persona_names = value

    @property
    def crew_result(self):
        self.ensure_initialized()
        return st.session_state.crew_result

    @crew_result.setter
    def crew_result(self, value):
        self.ensure_initialized()
        st.session_state.crew_result = value

    def next_step(self):
        self.step += 1
        st.rerun()

    def prev_step(self):
        self.step -= 1
        st.rerun()

    def reset(self):
        self.ensure_initialized()
        st.session_state.step = 1
        st.session_state.cv_content = ""
        st.session_state.cv_filename = ""
        st.session_state.job = JobInfo()
        st.session_state.crew_result = None
        st.session_state.interview_questions = []
        st.session_state.user_answers = {}
        st.session_state.interview_done = False
        st.session_state.board_agents = []
        st.session_state.selected_persona_names = ["LinkedIn Matchmaker (matchmaker)"]
        st.session_state.generate_cover_letter = False
        st.session_state.debate_mode = False
        st.session_state.interview_prep = ""
        st.session_state.token_usage = None
        st.session_state.history_saved = False
        st.session_state.compare_jobs = []
        st.session_state.demo_mode = False
        st.rerun()

    def update_config(self, **kwargs):
        self.ensure_initialized()
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def update_job(self, **kwargs):
        self.ensure_initialized()
        for key, value in kwargs.items():
            if hasattr(self.job, key):
                setattr(self.job, key, value)


# Singleton instance for easy access
state_manager = StateManager()

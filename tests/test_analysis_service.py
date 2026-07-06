"""Tests for crew wiring in AnalysisService (no LLM calls are made)."""

from types import SimpleNamespace

import pytest

from models import AppConfig, Persona
from services.analysis_service import (
    ROLE_BOARD_HEAD,
    ROLE_COVER_LETTER,
    ROLE_DEVILS_ADVOCATE,
    ROLE_OPTIMIZER,
    ROLE_REFORMATTER,
    AnalysisService,
)


@pytest.fixture
def config():
    return AppConfig(llm_provider="Google", selected_model="gemini-2.0-flash-lite", api_key="test-key")


@pytest.fixture
def personas():
    return [
        Persona(name="Recruiter", role="Recruiter", goal="Assess the CV", backstory="You are a recruiter."),
        Persona(
            name="Matchmaker",
            role="Matchmaker",
            goal="Match to job",
            backstory="Match against: {job_description}",
        ),
    ]


def _roles(crew):
    return [agent.role for agent in crew.agents]


def test_base_crew_structure(config, personas):
    crew = AnalysisService.create_analysis_crew(personas, "cv text", "job text", config)
    roles = _roles(crew)
    # 2 specialists + board head + optimizer + reformatter
    assert len(crew.agents) == 5
    assert len(crew.tasks) == 5
    assert ROLE_BOARD_HEAD in roles
    assert ROLE_OPTIMIZER in roles
    assert ROLE_REFORMATTER in roles
    assert ROLE_COVER_LETTER not in roles
    assert ROLE_DEVILS_ADVOCATE not in roles


def test_job_description_formatted_into_backstory(config, personas):
    crew = AnalysisService.create_analysis_crew(personas, "cv text", "THE_JOB", config)
    matchmaker = next(a for a in crew.agents if a.role == "Matchmaker")
    assert "THE_JOB" in matchmaker.backstory


def test_cover_letter_adds_agent(config, personas):
    crew = AnalysisService.create_analysis_crew(personas, "cv", "job", config, include_cover_letter=True)
    assert ROLE_COVER_LETTER in _roles(crew)
    assert len(crew.tasks) == 6


def test_debate_mode_adds_devils_advocate(config, personas):
    crew = AnalysisService.create_analysis_crew(personas, "cv", "job", config, debate_mode=True)
    assert ROLE_DEVILS_ADVOCATE in _roles(crew)
    assert len(crew.tasks) == 6


def test_configure_llm_provider_prefixes(config):
    assert AnalysisService._configure_llm(config).model == "gemini/gemini-2.0-flash-lite"

    anthropic_config = AppConfig(llm_provider="Anthropic", selected_model="claude-haiku-4-5", api_key="k")
    assert AnalysisService._configure_llm(anthropic_config).model == "anthropic/claude-haiku-4-5"

    ollama_config = AppConfig(llm_provider="Ollama", selected_model="llama3.1", api_key="")
    assert AnalysisService._configure_llm(ollama_config).model == "ollama/llama3.1"

    openai_config = AppConfig(llm_provider="OpenAI", selected_model="gpt-4o-mini", api_key="k")
    assert AnalysisService._configure_llm(openai_config).model == "gpt-4o-mini"


def test_get_output_by_role():
    result = SimpleNamespace(
        tasks_output=[
            SimpleNamespace(agent=ROLE_BOARD_HEAD, raw="board!"),
            SimpleNamespace(agent=ROLE_REFORMATTER, raw="cv!"),
        ]
    )
    assert AnalysisService.get_output_by_role(result, ROLE_BOARD_HEAD) == "board!"
    assert AnalysisService.get_output_by_role(result, ROLE_REFORMATTER) == "cv!"
    assert AnalysisService.get_output_by_role(result, ROLE_COVER_LETTER) is None


def test_kickoff_with_retry_retries_then_succeeds(mocker):
    crew = mocker.Mock()
    crew.kickoff.side_effect = [RuntimeError("transient"), "result"]
    mocker.patch("services.analysis_service.time.sleep")
    assert AnalysisService.kickoff_with_retry(crew, max_retries=2) == "result"
    assert crew.kickoff.call_count == 2


def test_kickoff_with_retry_raises_after_exhaustion(mocker):
    crew = mocker.Mock()
    crew.kickoff.side_effect = RuntimeError("permanent")
    mocker.patch("services.analysis_service.time.sleep")
    with pytest.raises(RuntimeError):
        AnalysisService.kickoff_with_retry(crew, max_retries=1)
    assert crew.kickoff.call_count == 2


def test_generate_next_round_prep_uses_timeline(mocker, config):
    fake_llm = mocker.Mock()
    fake_llm.call.return_value = "## Prep"
    mocker.patch.object(AnalysisService, "_configure_llm", return_value=fake_llm)

    result = AnalysisService.generate_next_round_prep(
        cv_markdown="# CV body",
        job_snippet="Senior Backend Engineer at Nimbus",
        timeline="- [2026-07-01] Interview: struggled with K8s autoscaling",
        config=config,
    )

    assert result == "## Prep"
    prompt = fake_llm.call.call_args[0][0]
    assert "# CV body" in prompt
    assert "struggled with K8s autoscaling" in prompt
    assert "Senior Backend Engineer at Nimbus" in prompt


def test_generate_next_round_prep_empty_timeline(mocker, config):
    fake_llm = mocker.Mock()
    fake_llm.call.return_value = "ok"
    mocker.patch.object(AnalysisService, "_configure_llm", return_value=fake_llm)

    AnalysisService.generate_next_round_prep("cv", "job", "", config)
    assert "(no entries logged yet)" in fake_llm.call.call_args[0][0]

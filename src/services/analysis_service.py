import time
from typing import Any, Callable, List, Optional, Tuple

from crewai import LLM, Agent, Crew, Process, Task

from llm_utils import get_ollama_base_url
from logger import logger
from models import AppConfig, Persona
from prompts import (
    BOARD_HEAD_BACKSTORY,
    BOARD_HEAD_TASK_DESCRIPTION,
    COVER_LETTER_AGENT_BACKSTORY,
    COVER_LETTER_TASK_DESCRIPTION,
    DEVILS_ADVOCATE_BACKSTORY,
    DEVILS_ADVOCATE_TASK_DESCRIPTION,
    INTERVIEW_PREP_PROMPT,
    INTERVIEW_QUESTIONS_PROMPT,
    OPTIMIZER_AGENT_BACKSTORY,
    OPTIMIZER_TASK_DESCRIPTION,
    REFORMATTER_AGENT_BACKSTORY,
    REFORMATTER_TASK_DESCRIPTION,
)

# Agent role names - the results UI matches task outputs by these
ROLE_BOARD_HEAD = "Board Head for CV Excellence"
ROLE_OPTIMIZER = "Targeted Resume Optimizer"
ROLE_REFORMATTER = "Expert CV Reformatter"
ROLE_COVER_LETTER = "Cover Letter Writer"
ROLE_DEVILS_ADVOCATE = "Devil's Advocate"


class AnalysisService:
    @staticmethod
    def _configure_llm(config: AppConfig) -> LLM:
        """Builds the LLM instance for the configured provider.

        API keys are passed explicitly to the LLM object and never written to
        process-wide environment variables (which would leak between users on
        a shared host).
        """
        if config.llm_provider == "Google":
            return LLM(model=f"gemini/{config.selected_model}", api_key=config.api_key)
        if config.llm_provider == "Anthropic":
            return LLM(model=f"anthropic/{config.selected_model}", api_key=config.api_key)
        if config.llm_provider == "Ollama":
            return LLM(model=f"ollama/{config.selected_model}", base_url=get_ollama_base_url())
        # OpenAI: CrewAI expects "gpt-4o" or "openai/gpt-4o"
        return LLM(model=config.selected_model, api_key=config.api_key)

    @staticmethod
    def _create_specialist_agents(
        personas: List[Persona], cv_content: str, job_description: str, model: LLM
    ) -> Tuple[List[Agent], List[Task]]:
        """Creates specialist agents and their analysis tasks."""
        agents = []
        tasks = []

        for persona in personas:
            backstory = persona.backstory
            if "{job_description}" in backstory:
                backstory = backstory.format(job_description=job_description)

            specialist_agent = Agent(
                role=persona.name,
                goal=persona.goal,
                backstory=backstory,
                llm=model,
                verbose=True,
                allow_delegation=False,
            )

            specialist_task = Task(
                description=(
                    f"Analyze the candidate's CV: {cv_content[:15000]} based on your expertise. "
                    f"Consider the job description: {job_description}"
                ),
                expected_output=f"A detailed critique from the perspective of a {persona.name}.",
                agent=specialist_agent,
                async_execution=True,
            )
            agents.append(specialist_agent)
            tasks.append(specialist_task)

        return agents, tasks

    @staticmethod
    def create_analysis_crew(
        selected_personas: List[Persona],
        cv_content: str,
        job_description: str,
        config: AppConfig,
        user_answers: str = "",
        task_callback: Optional[Callable[[Any], None]] = None,
        include_cover_letter: bool = False,
        debate_mode: bool = False,
    ) -> Crew:
        """Creates and configures a CrewAI crew for CV analysis using domain models."""

        logger.info(
            f"Creating analysis crew with {len(selected_personas)} specialists "
            f"(cover_letter={include_cover_letter}, debate={debate_mode})..."
        )

        crew_model = AnalysisService._configure_llm(config)

        agents = []
        tasks = []

        # 1. Specialist Agents
        specialist_agents, specialist_tasks = AnalysisService._create_specialist_agents(
            selected_personas, cv_content, job_description, crew_model
        )
        agents.extend(specialist_agents)
        tasks.extend(specialist_tasks)

        board_head_context = list(specialist_tasks)

        # 2. Optional debate round: a Devil's Advocate critiques the specialists
        if debate_mode:
            devils_advocate = Agent(
                role=ROLE_DEVILS_ADVOCATE,
                goal="Stress-test the specialists' findings before the final synthesis.",
                backstory=DEVILS_ADVOCATE_BACKSTORY,
                llm=crew_model,
                verbose=True,
                allow_delegation=False,
            )
            critique_task = Task(
                description=DEVILS_ADVOCATE_TASK_DESCRIPTION,
                expected_output="A concise critique of the specialist reports.",
                agent=devils_advocate,
                context=specialist_tasks,
                callback=task_callback,
            )
            agents.append(devils_advocate)
            tasks.append(critique_task)
            board_head_context.append(critique_task)

        # 3. Board Head (Synthesizer)
        board_head = Agent(
            role=ROLE_BOARD_HEAD,
            goal="Synthesize all specialist findings into one final actionable recommendation",
            backstory=BOARD_HEAD_BACKSTORY,
            llm=crew_model,
            verbose=True,
            allow_delegation=False,
        )

        final_recommendation_task = Task(
            description=BOARD_HEAD_TASK_DESCRIPTION,
            expected_output="A comprehensive board recommendation report focusing on critique and strategic advice.",
            agent=board_head,
            context=board_head_context,
            callback=task_callback,
        )
        agents.append(board_head)
        tasks.append(final_recommendation_task)

        # 4. Minimal Changes Agent
        optimizer_agent = Agent(
            role=ROLE_OPTIMIZER,
            goal="Identify specific keywords and phrasing tweaks to align with the job description.",
            backstory=OPTIMIZER_AGENT_BACKSTORY,
            llm=crew_model,
            verbose=True,
            allow_delegation=False,
        )

        optimization_task = Task(
            description=OPTIMIZER_TASK_DESCRIPTION.format(
                cv_content_snippet=cv_content[:15000], job_description=job_description
            ),
            expected_output="A conversational list of high-impact advice and specific phrasing recommendations.",
            agent=optimizer_agent,
            callback=task_callback,
        )
        agents.append(optimizer_agent)
        tasks.append(optimization_task)

        # 5. Reformatter Agent (Final CV)
        reformatter_agent = Agent(
            role=ROLE_REFORMATTER,
            goal="Rewrite the candidate CV into a professional, modern Markdown format incorporating board feedback.",
            backstory=REFORMATTER_AGENT_BACKSTORY,
            llm=crew_model,
            verbose=True,
            allow_delegation=False,
        )

        reformat_task = Task(
            description=REFORMATTER_TASK_DESCRIPTION.format(cv_content_snippet=cv_content[:15000], user_answers=user_answers),
            expected_output="The complete, polished CV with all original sections and minimal improvements, formatted in clean Markdown.",
            agent=reformatter_agent,
            context=[optimization_task],
            callback=task_callback,
        )
        agents.append(reformatter_agent)
        tasks.append(reformat_task)

        # 6. Optional Cover Letter Writer
        if include_cover_letter:
            cover_letter_agent = Agent(
                role=ROLE_COVER_LETTER,
                goal="Write a tailored cover letter and outreach messages for this specific job.",
                backstory=COVER_LETTER_AGENT_BACKSTORY,
                llm=crew_model,
                verbose=True,
                allow_delegation=False,
            )
            cover_letter_task = Task(
                description=COVER_LETTER_TASK_DESCRIPTION.format(
                    cv_content_snippet=cv_content[:15000], job_description=job_description
                ),
                expected_output="A tailored cover letter, LinkedIn note, and follow-up email in Markdown.",
                agent=cover_letter_agent,
                context=[final_recommendation_task],
                callback=task_callback,
            )
            agents.append(cover_letter_agent)
            tasks.append(cover_letter_task)

        # Speed optimization: memory disabled
        analysis_crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
        )

        logger.info("Analysis crew successfully created.")
        return analysis_crew

    @staticmethod
    def kickoff_with_retry(crew: Crew, max_retries: int = 2, base_delay: float = 5.0):
        """Runs the crew, retrying with exponential backoff on transient failures."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return crew.kickoff()
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    logger.warning(f"Crew kickoff failed (attempt {attempt + 1}): {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        logger.error(f"Crew kickoff failed after {max_retries + 1} attempts: {last_error}")
        raise last_error

    @staticmethod
    def get_output_by_role(result, role_keyword: str) -> Optional[str]:
        """Finds a task output in a CrewOutput by (partial) agent role name."""
        tasks_output = getattr(result, "tasks_output", None) or []
        for task_output in reversed(tasks_output):
            agent = getattr(task_output, "agent", "")
            role = getattr(agent, "role", agent)
            if role_keyword in str(role):
                return task_output.raw
        return None

    @staticmethod
    def get_token_usage(result) -> Optional[dict]:
        """Extracts token usage metrics from a CrewOutput, if available."""
        usage = getattr(result, "token_usage", None)
        if usage is None:
            return None
        if isinstance(usage, dict):
            return usage
        if hasattr(usage, "model_dump"):
            return usage.model_dump()
        if hasattr(usage, "__dict__"):
            return dict(usage.__dict__)
        return None

    @staticmethod
    def generate_interview_questions(cv_content: str, config: AppConfig) -> List[str]:
        """Generates up to 4 interview questions for the personalization step."""
        llm = AnalysisService._configure_llm(config)
        response = llm.call(INTERVIEW_QUESTIONS_PROMPT.format(cv_content=cv_content[:4000]))
        questions = [q.strip() for q in str(response).split("\n") if q.strip() and q.strip()[0].isdigit()]
        return questions[:4]

    @staticmethod
    def generate_interview_prep(cv_content: str, job_description: str, board_report: str, config: AppConfig) -> str:
        """Generates an interview preparation guide from the board's findings."""
        llm = AnalysisService._configure_llm(config)
        response = llm.call(
            INTERVIEW_PREP_PROMPT.format(
                cv_content=cv_content[:8000],
                job_description=job_description[:6000],
                board_report=board_report[:8000],
            )
        )
        return str(response)

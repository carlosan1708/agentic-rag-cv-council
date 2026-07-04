# AI - CV Advisor Board 📄🤖

# Live Demo: https://ai-cv-advisory-board.streamlit.app/

An AI-powered multi-agent system designed to analyze and optimize CVs. It uses **CrewAI** and **Streamlit** with **Google Gemini**, **OpenAI**, **Anthropic Claude** or local **Ollama** models to compare your CV against job descriptions and provide expert feedback from a "Board" of specialized agents.

[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)

## 🚀 Overview

Collaborative AI deliberation to perfect your CV. Specialized AI agents (the "Board") review your CV from multiple perspectives, providing actionable feedback, an ATS match score, a professionally rewritten version, a tailored cover letter and interview preparation.

![Demo](Demo.gif)

## ✨ Features

- **Step-by-Step Wizard**: A guided process (Welcome, Config, Upload, Job, Team, Results).
- **Multi-Agent Collaboration**: Powered by **CrewAI** for sophisticated AI deliberation, with an optional
  **Debate Round** where a Devil's Advocate challenges the specialists before the final synthesis.
- **ATS Match Score**: Instant, deterministic keyword & structure scoring — including a before/after
  comparison of your original vs. optimized CV, and a **multi-job comparison** to decide where to apply.
- **Job Targeting**: Extract job descriptions from LinkedIn, Indeed, Greenhouse, Lever and most other
  boards (schema.org JobPosting parsing), or paste them manually.
- **Custom Specialist Board**: 11 persona packs (tech, product, finance, healthcare, academia,
  sales & marketing, data & AI, ...) plus a **Persona Builder** with YAML export.
- **Professional Rewrite**: Get an optimized version of your CV as Markdown, **PDF** (Unicode-aware) or **DOCX**.
- **Cover Letter & Outreach**: Optional tailored cover letter, LinkedIn note and follow-up email.
- **Interview Prep**: Likely questions with STAR model answers built from the board's gap analysis.
- **Local History**: Past analyses are stored locally (SQLite) with one-click "delete my data".
- **Multi-Provider**: Google Gemini, OpenAI, Anthropic Claude, or fully local via Ollama.
- **Cost Transparency**: Token usage reported after every run; retry with backoff on transient failures.

## 🏗️ Project Architecture

The application follows a scalable, service-oriented architecture designed for maintainability and growth:

```text
.
├── personas/           # YAML persona packs (role/goal/backstory schema)
├── src/                # Application source code
│   ├── app.py          # Main Streamlit entry point
│   ├── models.py       # Domain data models (Job, Persona, Config)
│   ├── state_manager.py# Centralized session state orchestration
│   ├── scraper.py      # Job posting extraction (JSON-LD + selectors)
│   ├── logger.py       # Structured application logging
│   ├── exceptions.py   # Custom domain exceptions
│   ├── services/       # Stateless business logic layer
│   │   ├── analysis_service.py # CrewAI orchestration (board, debate, cover letter)
│   │   ├── ats_service.py      # Deterministic ATS scoring & keyword analysis
│   │   ├── cv_service.py       # PDF/DOCX/TXT parsing & PDF/DOCX generation
│   │   ├── history_service.py  # Local SQLite persistence of analyses
│   │   ├── job_service.py      # Job scraping & extraction
│   │   ├── persona_service.py  # Persona management
│   │   └── config_service.py   # LLM & System configuration
│   └── steps/          # Modular UI components for the wizard
├── scripts/            # Development and CI/CD utilities
├── tests/              # Automated test suite (pytest)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container image (see docker-compose.yml)
├── .env.example        # Template for environment variables
└── README.md           # Project documentation
```

### Core Design Principles
- **Separation of Concerns**: UI code is decoupled from business logic.
- **Stateless Services**: Logic is encapsulated in reusable services.
- **Centralized State**: Application state is managed through a single `StateManager`.
- **Observability**: Built-in structured logging and custom error handling.
- **Privacy**: CVs are processed in memory and never logged; API keys are kept per-session and never
  written to shared environment variables; analysis history stays on your machine.

## Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- An API key for Google AI (Gemini), OpenAI or Anthropic — or a local [Ollama](https://ollama.com/) server (no key needed)

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/carlosan1708/ai-cv-advisor-board
cd ai-cv-advisor-board
```

### 2. Set Up the Python Environment

#### On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### On Windows:
```bash
python -m venv venv
.\venv\Scripts\activate
```

#### Install Dependencies:
```bash
pip install -r requirements.txt
```

#### Development Setup (Optional):
If you plan to contribute, install development tools and pre-commit hooks:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

To run pre-commit checks manually on all files:

```bash
pre-commit run --all-files
```

### 3. Environment Setup

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` and add your `GOOGLE_API_KEY` (or other keys as needed).

### 4. Run the Application

```bash
streamlit run src/app.py
```

The application will be available at `http://localhost:8501`.

### Alternative: Run with Docker

```bash
cp .env.example .env   # add your keys
docker compose up --build
```

## 🧪 Testing

```bash
python -m pytest
```

CI runs linting and the full test suite on every push and pull request.

## 🎭 Personas

Personas are plain YAML files in `personas/` — the easiest way to contribute. See
[docs/PERSONAS.md](docs/PERSONAS.md) for the schema and a contribution guide. You can also build
custom personas in-app (Step 4) and export them as YAML.

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **Agent Orchestration**: [CrewAI](https://www.crewai.com/)
- **LLM Framework**: [LiteLLM](https://www.litellm.ai/)
- **LLMs**: [Google Gemini](https://ai.google.dev/) (default), [OpenAI](https://openai.com/), [Anthropic Claude](https://www.anthropic.com/), [Ollama](https://ollama.com/) (local)
- **Documents**: [PyPDF](https://pypi.org/project/pypdf/), [FPDF2](https://py-pdf.github.io/fpdf2/), [python-docx](https://python-docx.readthedocs.io/)

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-NoDerivs 4.0 International (CC BY-NC-ND 4.0)** License. See the [LICENSE](LICENSE) file for details.

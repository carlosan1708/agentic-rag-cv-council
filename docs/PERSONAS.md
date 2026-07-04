# Personas Guide

Personas define the specialists on the CV Advisory Board. Each persona becomes a CrewAI agent that
reviews the CV from its own perspective. They live as YAML files in the `personas/` directory —
adding one is the easiest way to contribute to this project.

## Schema

Each `personas/*.yaml` file contains a **list** of personas:

```yaml
- name: "Investment Banking MD"                     # Display name (required)
  role: "Managing Director at an investment bank"   # Who the agent is (required)
  goal: "Assess deal experience and quantitative rigor"  # What it optimizes for (required)
  backstory: |                                      # Full instructions (required)
    You are a Managing Director in investment banking. Analyze the CV for finance-industry readiness.
    - Every experience bullet should quantify deal size, portfolio value or P&L impact.
    - Critique vague claims without the candidate's specific contribution.
```

Notes:

- `backstory` may include the `{job_description}` placeholder — it is replaced with the target job
  description at analysis time (see `matchmaker.yaml` for examples).
- The legacy schema (`name` + `prompt`) still loads for backwards compatibility, but new personas
  should use the full schema above.
- Persona display names in the UI are `"{name} ({filename})"`, so names only need to be unique
  within a file.

## Shipped packs

| File | Focus |
|------|-------|
| `general.yaml` | Technical recruiter, soft skills coach |
| `matchmaker.yaml` | Job-description matching, cultural fit |
| `it_specialist.yaml` | Architect, tech lead, SRE |
| `product_design.yaml` | Product strategy, UX |
| `startup_specialist.yaml` | Founder/VC perspective |
| `executive.yaml` | Executive branding, CFO/ROI |
| `finance.yaml` | Investment banking, risk & compliance |
| `healthcare.yaml` | Clinical operations, health-tech |
| `academia.yaml` | Faculty search, PhD-to-industry transition |
| `sales_marketing.yaml` | Sales leadership, growth marketing |
| `data_ai.yaml` | Data science, AI engineering |

## Writing a good persona

1. **Give it a strong identity** — "You are a CFO" beats "You are an expert".
2. **List concrete evaluation criteria** as bullets; the agent follows them closely.
3. **Ask for specifics** — metrics, named tools/frameworks, rewritten example bullets.
4. **Keep it focused** — one lens per persona; add a second persona instead of a second topic.

## Testing

`tests/test_personas.py` validates every YAML file (schema + loadability). Run:

```bash
python -m pytest tests/test_personas.py
```

## In-app Persona Builder

Users can create custom personas in Step 4 ("Assemble Your Board") and export them as YAML with the
"Export custom personas as YAML" button — exported files can be dropped into `personas/` directly or
submitted as a pull request.

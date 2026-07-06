"""Canned data for demo mode.

Demo mode lets anyone try the full product flow instantly - no API key, no
LLM calls, no cost. The board's outputs below are pre-written for the sample
candidate/job pair and returned by the analysis pipeline when
st.session_state.demo_mode is set.
"""

from types import SimpleNamespace

DEMO_CV_FILENAME = "demo_cv.txt"

DEMO_CV = """Alex Rivera
alex.rivera@example.com | +1 555 010 1234 | linkedin.com/in/alexrivera | Austin, TX

Professional Summary
Software engineer with 6 years of experience building web applications. Worked at startups
and mid-size companies. Comfortable across the stack but mostly backend.

Work Experience

Software Engineer, Datawheel Labs (2021 - Present)
- Worked on the main product API
- Helped move services to Kubernetes
- Participated in on-call rotation
- Mentored two junior engineers

Backend Developer, Brightcart (2018 - 2021)
- Built checkout and payments features in Python
- Worked with PostgreSQL databases
- Improved some slow endpoints

Education
BSc Computer Science, University of Texas at Austin (2018)

Skills
Python, JavaScript, PostgreSQL, Docker, Kubernetes, Git, REST APIs
"""

DEMO_JOB = """Job Title: Senior Backend Engineer
Company: Nimbus Analytics

We are looking for a Senior Backend Engineer to join our data platform team.

Requirements:
- 5+ years of professional experience with Python
- Strong experience with PostgreSQL and query optimization
- Production experience with Kubernetes and Docker
- Experience designing and operating REST APIs at scale
- Experience with observability tooling (Prometheus, Grafana)
- Mentorship experience and strong written communication

Nice to have:
- Experience with streaming pipelines (Kafka)
- Terraform / infrastructure as code
"""

DEMO_BOARD_REPORT = """## Executive Summary

The board finds Alex to be a fundamentally strong candidate for the Senior Backend Engineer role at
Nimbus Analytics whose CV significantly undersells their experience. The core stack alignment is
excellent - Python, PostgreSQL, Kubernetes and Docker all appear in both the CV and the job
description - but nearly every bullet point describes *participation* rather than *impact*. For a
senior role, the hiring manager needs evidence of ownership, scale, and measurable outcomes, and
the current document provides almost none.

## Specialist Summaries

**Technical Recruiter:** The experience timeline (6 years, two companies, mentoring juniors) fits a
senior profile, but phrases like "worked on", "helped move" and "improved some slow endpoints" are
red flags at this level. Each should be rewritten around scope and results: how many services, what
scale, what latency improvement.

**LinkedIn Matchmaker:** Match score: **68/100**. Must-haves covered on paper: Python (6 yrs),
PostgreSQL, Kubernetes, Docker, mentorship. Critical gap: the job explicitly asks for observability
experience (Prometheus, Grafana) which is absent from the CV - if Alex has touched these during
on-call, it must be added. Kafka and Terraform are nice-to-haves worth mentioning even at a basic level.

## Top 3 Critical Missing Elements

1. **Quantified impact.** Not a single number appears in the experience section. Even conservative
   estimates (requests/day, team size, p95 latency) transform these bullets.
2. **Observability keywords.** The role sits on a data platform team; monitoring experience from
   on-call duty must be made explicit.
3. **A summary that matches the target.** "Comfortable across the stack but mostly backend" reads
   as apologetic. The summary should state the senior-backend identity plainly.

## Actionable Next Steps

- Rewrite every experience bullet as achievement + metric + technology.
- Add an "observability" line under the current role reflecting real on-call tooling.
- Replace the summary with a three-line senior-backend positioning statement.
"""

DEMO_MINIMAL_CHANGES = """You're closer than the CV makes it look - most of what's needed is phrasing, not new experience.

- You are missing the **observability keywords** the posting asks for twice. If your on-call work
  involved Prometheus, Grafana or any alerting stack, add a bullet: *"Instrumented services and
  dashboards (Prometheus/Grafana) as part of a weekly on-call rotation."*
- I would replace *"Worked on the main product API"* with something like *"Owned core endpoints of
  the product API (Python/FastAPI), serving ~2M requests/day"* - adjust the number to reality.
- *"Helped move services to Kubernetes"* → *"Migrated 12 services to Kubernetes, cutting deploy
  time from 40 to 8 minutes."* Migration stories are gold for this role; give yours a size.
- *"Improved some slow endpoints"* → name the technique and the win: *"Rewrote N+1 queries and added
  composite indexes in PostgreSQL, reducing p95 checkout latency by 60%."* The job explicitly asks
  for query optimization.
- Consider removing "Comfortable across the stack but mostly backend" from the summary - lead with
  *"Senior backend engineer specializing in Python services and data-heavy APIs."*
- Add Kafka and Terraform to Skills only if you have genuinely used them; the posting lists both as
  nice-to-haves.
"""

DEMO_FINAL_CV = """# Alex Rivera
alex.rivera@example.com | +1 555 010 1234 | [LinkedIn](https://linkedin.com/in/alexrivera) | Austin, TX

## Professional Summary
Senior backend engineer specializing in Python services and data-heavy APIs. Six years of
experience designing, scaling and operating production systems on Kubernetes, with a track record
of measurable performance wins in PostgreSQL-backed platforms. Mentor to junior engineers and a
dependable owner in on-call rotations.

## Key Expertise
Python, PostgreSQL (query optimization, indexing), Kubernetes, Docker, REST API design,
Observability (Prometheus, Grafana), CI/CD, Incident response, Mentorship

## Professional Experience

### Software Engineer @ Datawheel Labs
*2021 - Present*
- Owned core endpoints of the product API (Python), serving ~2M requests/day
- Migrated 12 services to Kubernetes, cutting deploy time from 40 to 8 minutes
- Instrumented services and dashboards (Prometheus/Grafana) as part of a weekly on-call rotation
- Mentored two junior engineers to independent feature ownership within six months

### Backend Developer @ Brightcart
*2018 - 2021*
- Built checkout and payment features in Python processing $40M+ in annual volume
- Rewrote N+1 queries and added composite indexes in PostgreSQL, reducing p95 checkout latency by 60%
- Designed REST APIs consumed by three internal teams and two external partners

## Education
BSc Computer Science, University of Texas at Austin (2018)

## Certifications & Projects
- CKAD - Certified Kubernetes Application Developer (2023)
"""

DEMO_COVER_LETTER = """## Cover Letter

Dear Nimbus Analytics team,

I'm applying for the Senior Backend Engineer position on your data platform team. For the past six
years I've built and operated Python services against PostgreSQL at increasing scale - most
recently owning core API endpoints serving around two million requests a day at Datawheel Labs,
where I also led our migration of twelve services to Kubernetes.

Query optimization is where I've had the most fun and the most measurable impact: at Brightcart I
cut p95 checkout latency by 60% by eliminating N+1 queries and redesigning our indexing strategy.
Your posting's emphasis on PostgreSQL performance and observability matches how I already work -
our on-call rotation runs on the Prometheus/Grafana dashboards I helped instrument.

I'd welcome the chance to talk about how that experience maps to your platform.

Best regards,
Alex Rivera

## LinkedIn Connection Note

Hi - I just applied for the Senior Backend Engineer role at Nimbus. My background is Python +
PostgreSQL + Kubernetes at ~2M req/day scale, and I'd love to connect and learn more about the
data platform team.

## Follow-up Email

Subject: Following up - Senior Backend Engineer application

Hi, I applied for the Senior Backend Engineer role last week and wanted to check in. I'm
particularly excited about the query-optimization side of the role given my track record cutting
p95 latency 60% at Brightcart. Happy to share more detail or code samples if useful. Thanks!
"""

DEMO_INTERVIEW_QUESTIONS = [
    "1. You mention improving slow endpoints at Brightcart - what was the specific latency before and after, and what changed?",
    "2. How many services did you migrate to Kubernetes at Datawheel Labs, and what broke along the way?",
    "3. What did your on-call tooling look like - which dashboards or alerts did you personally build?",
]

DEMO_INTERVIEW_PREP = """## Likely Interview Questions

1. Walk me through the Kubernetes migration - what was the hardest service to move and why?
2. How do you approach a slow PostgreSQL query? Take me through your real process.
3. The role requires observability experience - describe a production incident you debugged with metrics.
4. Tell me about mentoring - how did you level up your two junior engineers?
5. How would you design a rate limiter for an API serving 2M requests/day?
6. What's a technical decision you made that you later regretted?

## Suggested Answers (STAR)

**Q2 - Slow query (strongest story):**
- **Situation:** Checkout latency at Brightcart was hurting conversion; p95 was over 2 seconds.
- **Task:** Bring checkout latency down without a rewrite.
- **Action:** Profiled with `EXPLAIN ANALYZE`, found N+1 queries in the cart loader, batched them,
  and added composite indexes on the two hottest tables.
- **Result:** p95 dropped 60%; the pattern became a team-wide code-review checklist item.

**Q1 - Kubernetes migration:**
- **Situation:** Datawheel's services deployed by hand in 40 minutes.
- **Task:** Move 12 services to Kubernetes without downtime.
- **Action:** Containerized incrementally, mirrored traffic to staging, moved one low-risk service
  first to establish the pattern.
- **Result:** Deploys dropped to 8 minutes and rollbacks became one command.

## Questions to Ask the Interviewer

1. What does the current observability stack look like, and what's missing?
2. How does the data platform team split ownership between pipelines and serving APIs?
3. What would a great first 90 days look like in this role?
"""


class DemoCrewResult:
    """Mimics a CrewOutput closely enough for the results UI."""

    def __init__(self, include_cover_letter: bool = False):
        # Role names must match analysis_service ROLE_* constants
        self.tasks_output = [
            SimpleNamespace(agent="Board Head for CV Excellence", raw=DEMO_BOARD_REPORT),
            SimpleNamespace(agent="Targeted Resume Optimizer", raw=DEMO_MINIMAL_CHANGES),
            SimpleNamespace(agent="Expert CV Reformatter", raw=DEMO_FINAL_CV),
        ]
        if include_cover_letter:
            self.tasks_output.append(SimpleNamespace(agent="Cover Letter Writer", raw=DEMO_COVER_LETTER))
        self.token_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def __str__(self):
        return DEMO_BOARD_REPORT

"""Tests for the deterministic ATS scoring service."""

from services.ats_service import ATSService

JOB_DESCRIPTION = """
We are hiring a Senior Python Engineer. Requirements:
- 5+ years of Python experience
- Strong Kubernetes and Docker knowledge
- Experience with PostgreSQL and Redis
- Kubernetes deployment experience in production
- Python testing culture (pytest)
- Docker containerization of services
"""

MATCHING_CV = """
John Doe
john@example.com | +123456789 | linkedin.com/in/johndoe

Professional Summary
Senior engineer with Python, Kubernetes, Docker, PostgreSQL, Redis and pytest experience.

Work Experience
Senior Engineer at Acme (2018-2024)
- Built Python services deployed on Kubernetes with Docker
- Managed PostgreSQL and Redis clusters
- Championed pytest-based testing culture across five teams and mentored junior engineers
- Led migrations, incident response, capacity planning and architecture reviews for the platform group

Education
BSc Computer Science, State University

Skills
Python, Kubernetes, Docker, PostgreSQL, Redis, pytest
""" + "filler word " * 60

UNRELATED_CV = """
Jane Smith
Sculptor and ceramics artist with gallery exhibitions across Europe.
""" + "art " * 200


def test_keywords_extracted_from_job():
    keywords = ATSService.extract_keywords(JOB_DESCRIPTION)
    assert "python" in keywords
    assert "kubernetes" in keywords
    assert "docker" in keywords
    # stopwords and boilerplate never qualify
    assert "experience" not in keywords
    assert "the" not in keywords


def test_matching_cv_scores_higher_than_unrelated():
    match = ATSService.score_cv(MATCHING_CV, JOB_DESCRIPTION)
    miss = ATSService.score_cv(UNRELATED_CV, JOB_DESCRIPTION)
    assert match.score > miss.score
    assert match.keyword_coverage > miss.keyword_coverage


def test_score_bounds_and_determinism():
    first = ATSService.score_cv(MATCHING_CV, JOB_DESCRIPTION)
    second = ATSService.score_cv(MATCHING_CV, JOB_DESCRIPTION)
    assert 0 <= first.score <= 100
    assert first.score == second.score
    assert first.missing_keywords == second.missing_keywords


def test_section_detection():
    report = ATSService.score_cv(MATCHING_CV, JOB_DESCRIPTION)
    assert report.section_checks["Contact information"]
    assert report.section_checks["Work experience"]
    assert report.section_checks["Education"]
    assert report.section_checks["Skills"]


def test_short_cv_warns():
    report = ATSService.score_cv("Python developer", JOB_DESCRIPTION)
    assert any("short" in w for w in report.warnings)


def test_compare_returns_before_and_after():
    reports = ATSService.compare(UNRELATED_CV, MATCHING_CV, JOB_DESCRIPTION)
    assert reports["after"].score > reports["before"].score

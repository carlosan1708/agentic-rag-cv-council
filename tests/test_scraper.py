"""Tests for the job description extractor."""

import json

import pytest
import requests

import scraper
from exceptions import JobScrapingError
from scraper import extract_job_description

JSONLD_PAGE = """
<html><head>
<script type="application/ld+json">
{payload}
</script>
</head><body><p>irrelevant</p></body></html>
"""

LINKEDIN_PAGE = """
<html><body>
<div class="show-more-less-html__markup">
We are hiring a Python engineer.<br>Requirements: Kubernetes.
</div>
</body></html>
"""


class FakeResponse:
    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code}")


def _mock_get(mocker, html: str):
    mocker.patch.object(scraper.requests, "get", return_value=FakeResponse(html))


def test_jsonld_jobposting_extracted(mocker):
    payload = json.dumps(
        {
            "@type": "JobPosting",
            "title": "Senior Python Engineer",
            "hiringOrganization": {"@type": "Organization", "name": "Acme"},
            "description": "<p>Build <b>great</b> software with Python.</p>",
        }
    )
    _mock_get(mocker, JSONLD_PAGE.format(payload=payload))

    result = extract_job_description("https://example.com/job/1")
    assert "Job Title: Senior Python Engineer" in result
    assert "Company: Acme" in result
    assert "Build" in result and "great" in result
    assert "<p>" not in result


def test_jsonld_graph_wrapper(mocker):
    payload = json.dumps(
        {"@graph": [{"@type": "WebPage"}, {"@type": "JobPosting", "description": "Ship Python services daily."}]}
    )
    _mock_get(mocker, JSONLD_PAGE.format(payload=payload))

    result = extract_job_description("https://example.com/job/2")
    assert "Ship Python services daily." in result


def test_linkedin_selector_fallback(mocker):
    _mock_get(mocker, LINKEDIN_PAGE)
    result = extract_job_description("https://linkedin.com/jobs/view/123")
    assert "We are hiring a Python engineer." in result


def test_no_description_raises(mocker):
    _mock_get(mocker, "<html><body><nav>menu</nav></body></html>")
    with pytest.raises(JobScrapingError):
        extract_job_description("https://example.com/nothing")


def test_network_error_raises(mocker):
    mocker.patch.object(scraper.requests, "get", side_effect=requests.exceptions.ConnectionError("boom"))
    with pytest.raises(JobScrapingError):
        extract_job_description("https://example.com/down")


def test_empty_url_returns_empty():
    assert extract_job_description("") == ""

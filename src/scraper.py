"""Job description extraction from job posting URLs.

Extraction strategy (in order):
1. schema.org/JobPosting JSON-LD - used by LinkedIn, Indeed, Greenhouse, Lever,
   Workday and most job boards.
2. Known job-board HTML selectors (LinkedIn public views).
3. Generic main-content fallback (<main>/<article>).
"""

import json
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from exceptions import JobScrapingError

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Known job-board selectors, tried in order
DESCRIPTION_SELECTORS = [
    ("div", "description__text"),
    ("div", "show-more-less-html__markup"),
    ("section", "description"),
    ("div", "job-view-main-content"),
]


def _iter_jsonld_objects(data) -> List[dict]:
    """Flattens a JSON-LD payload (dict, list, or @graph) into a list of dicts."""
    if isinstance(data, list):
        objects = []
        for item in data:
            objects.extend(_iter_jsonld_objects(item))
        return objects
    if isinstance(data, dict):
        objects = [data]
        if "@graph" in data:
            objects.extend(_iter_jsonld_objects(data["@graph"]))
        return objects
    return []


def _extract_from_jsonld(soup: BeautifulSoup) -> Optional[str]:
    """Extracts a job description from schema.org/JobPosting JSON-LD, if present."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        for obj in _iter_jsonld_objects(data):
            obj_type = obj.get("@type", "")
            types = obj_type if isinstance(obj_type, list) else [obj_type]
            if "JobPosting" not in types:
                continue

            description = obj.get("description", "")
            if not description:
                continue

            # description is usually HTML - convert to plain text
            text = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True)

            parts = []
            title = obj.get("title")
            if title:
                parts.append(f"Job Title: {title}")
            org = obj.get("hiringOrganization")
            if isinstance(org, dict) and org.get("name"):
                parts.append(f"Company: {org['name']}")
            parts.append(text)
            return "\n".join(parts)
    return None


def _extract_from_selectors(soup: BeautifulSoup) -> Optional[str]:
    """Extracts a job description using known job-board CSS selectors."""
    for tag, class_name in DESCRIPTION_SELECTORS:
        element = soup.find(tag, class_=class_name)
        if element:
            return element.get_text(separator="\n", strip=True)
    return None


def _extract_from_main_content(soup: BeautifulSoup) -> Optional[str]:
    """Last-resort fallback: text of the page's <main> or <article> element."""
    for tag in ("main", "article"):
        element = soup.find(tag)
        if element:
            text = element.get_text(separator="\n", strip=True)
            # Require a minimum length so we don't return nav/boilerplate
            if len(text) > 200:
                return text
    return None


def extract_job_description(url: str) -> str:
    """Extracts the job description text from a job posting URL.

    Raises:
        JobScrapingError: if the page cannot be fetched or no description is found.
    """
    if not url.strip():
        return ""

    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise JobScrapingError(f"Could not fetch the job posting page: {e}") from e

    soup = BeautifulSoup(response.text, "html.parser")

    for extractor in (_extract_from_jsonld, _extract_from_selectors, _extract_from_main_content):
        content = extractor(soup)
        if content:
            return content

    raise JobScrapingError("Could not find a job description on the page. Please paste the job description manually.")

"""Deterministic (non-LLM) ATS-style scoring of a CV against a job description.

Instant, reproducible and free: keyword coverage, section detection and
length/format checks. Used for the score dashboard, before/after comparison
and multi-job matching.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List

# Common English words plus job-posting boilerplate that should never count as "keywords"
STOPWORDS = frozenset("""
    a about above after again all also an and any are as at be because been before being below between both
    but by can could did do does doing down during each few for from further had has have having he her here
    hers him his how i if in into is it its itself just me more most my no nor not now of off on once only or
    other our ours out over own same she should so some such than that the their theirs them then there these
    they this those through to too under until up very was we were what when where which while who whom why
    will with would you your yours
    ability able across including include includes required requirements require preferred plus years year
    experience work working strong excellent knowledge skills skill team candidate role position company
    responsibilities responsibility opportunity looking join must help ensure new using understanding related
    employment equal status benefits salary location remote hybrid onsite apply application job title day per
    etc well good great within based via least e.g i.e
    """.split())

# Section names an ATS (and recruiter) expects to find
SECTION_PATTERNS: Dict[str, str] = {
    "Contact information": r"(@|\bemail\b|\bphone\b|\blinkedin\b|\+\d{6,})",
    "Summary / profile": r"\b(summary|profile|about me|objective)\b",
    "Work experience": r"\b(experience|employment|work history|career)\b",
    "Education": r"\b(education|degree|university|bachelor|master|phd)\b",
    "Skills": r"\b(skills|expertise|technologies|competencies|tech stack)\b",
}

MIN_CV_WORDS = 150
MAX_CV_WORDS = 1400

# Tokens keep + # . - so "c++", "c#", ".net" and "ci/cd" style terms survive
_TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+#./-]*")

# Component weights (must sum to 100)
KEYWORD_WEIGHT = 60
SECTION_WEIGHT = 25
LENGTH_WEIGHT = 15


@dataclass
class ATSReport:
    score: int
    keyword_coverage: float  # 0.0 - 1.0
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    section_checks: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def _tokenize(text: str) -> List[str]:
    return [t.lower().strip(".-/") for t in _TOKEN_PATTERN.findall(text)]


class ATSService:
    @staticmethod
    def extract_keywords(job_description: str, limit: int = 30) -> List[str]:
        """Extracts the most important keywords from a job description.

        Keywords are non-stopword terms ranked by frequency; terms appearing
        only once still qualify if they look like technical tokens (contain
        digits or +/#/. characters, e.g. "python3", "c++", ".net").
        """
        counts: Dict[str, int] = {}
        for token in _tokenize(job_description):
            if len(token) < 3 or token in STOPWORDS:
                continue
            counts[token] = counts.get(token, 0) + 1

        def is_technical(term: str) -> bool:
            return any(c.isdigit() or c in "+#." for c in term)

        candidates = [t for t, c in counts.items() if c >= 2 or is_technical(t)]
        candidates.sort(key=lambda t: (-counts[t], t))
        return candidates[:limit]

    @staticmethod
    def score_cv(cv_content: str, job_description: str) -> ATSReport:
        """Scores a CV against a job description. Deterministic, no LLM calls."""
        keywords = ATSService.extract_keywords(job_description)
        cv_tokens = set(_tokenize(cv_content))
        cv_lower = cv_content.lower()

        matched = [k for k in keywords if k in cv_tokens or k in cv_lower]
        missing = [k for k in keywords if k not in matched]
        coverage = len(matched) / len(keywords) if keywords else 1.0

        section_checks = {name: bool(re.search(pattern, cv_lower)) for name, pattern in SECTION_PATTERNS.items()}
        section_ratio = sum(section_checks.values()) / len(section_checks)

        warnings: List[str] = []
        word_count = len(cv_content.split())
        length_ratio = 1.0
        if word_count < MIN_CV_WORDS:
            length_ratio = word_count / MIN_CV_WORDS
            warnings.append(f"CV looks short ({word_count} words). ATS and recruiters expect more detail.")
        elif word_count > MAX_CV_WORDS:
            length_ratio = 0.7
            warnings.append(f"CV looks long ({word_count} words). Consider trimming to ~2 pages.")

        for name, present in section_checks.items():
            if not present:
                warnings.append(f"Could not detect a '{name}' section.")

        score = round(coverage * KEYWORD_WEIGHT + section_ratio * SECTION_WEIGHT + length_ratio * LENGTH_WEIGHT)
        score = max(0, min(100, score))

        return ATSReport(
            score=score,
            keyword_coverage=coverage,
            matched_keywords=matched,
            missing_keywords=missing,
            section_checks=section_checks,
            warnings=warnings,
        )

    @staticmethod
    def compare(original_cv: str, rewritten_cv: str, job_description: str) -> Dict[str, ATSReport]:
        """Scores the original and the rewritten CV against the same job."""
        return {
            "before": ATSService.score_cv(original_cv, job_description),
            "after": ATSService.score_cv(rewritten_cv, job_description),
        }

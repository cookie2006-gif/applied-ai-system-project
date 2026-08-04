"""
Reliability harness for the recommendation agent.

Design:
- A test case is a (query, expected_criteria) pair. `expected_criteria` is a
  small dict of assertions that don't require identical output — e.g.
  "top pick's genre should be in {lofi, jazz, ambient}", "confidence label
  should be at least MEDIUM", "at most one artist repeats".
- The harness runs each case through the agent, evaluates each criterion,
  and produces a structured pass/fail table plus a summary.
- Results are emitted in two formats:
  - a human-readable Markdown report (for the README / model card),
  - a JSON dump (for downstream tooling or CI).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

from src.agent import AgentResult, RecommendationAgent
from src.recommender import load_songs


# Type alias: a criterion is a callable (AgentResult) → (bool, str)
Criterion = Callable[[AgentResult], Tuple[bool, str]]


# ---------- Criterion factories ------------------------------------

def top_genre_in(allowed: set) -> Criterion:
    def check(r: AgentResult) -> Tuple[bool, str]:
        if not r.recommendations:
            return False, "no recommendations returned"
        actual = r.recommendations[0][0]["genre"]
        return (actual in allowed), f"top-genre='{actual}', allowed={sorted(allowed)}"
    check.__name__ = f"top_genre_in_{'/'.join(sorted(allowed))}"
    return check


def confidence_at_least(label: str) -> Criterion:
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    threshold = order[label]

    def check(r: AgentResult) -> Tuple[bool, str]:
        actual_rank = order.get(r.critique.confidence_label, 0)
        return (actual_rank >= threshold,
                f"confidence={r.critique.confidence_label} vs required≥{label}")
    check.__name__ = f"confidence_at_least_{label}"
    return check


def unique_artists_in_top_k(min_unique: int) -> Criterion:
    def check(r: AgentResult) -> Tuple[bool, str]:
        artists = {s.get("artist", "") for s, _, _ in r.recommendations}
        return (len(artists) >= min_unique,
                f"unique artists in top-K = {len(artists)}, required ≥ {min_unique}")
    check.__name__ = f"unique_artists_in_top_k_{min_unique}"
    return check


def no_errors_or_crashes() -> Criterion:
    def check(r: AgentResult) -> Tuple[bool, str]:
        crashes = [e for e in r.log.events if e.get("level") == "error"]
        return (not crashes, f"error-events={len(crashes)}")
    check.__name__ = "no_errors_or_crashes"
    return check


def warns_on_unknown_input() -> Criterion:
    """Verify the agent flags an unknown-genre input rather than silently guessing."""
    def check(r: AgentResult) -> Tuple[bool, str]:
        warnings = r.parse.warnings
        has_genre_warning = any("no genre matched" in w for w in warnings)
        return (has_genre_warning, f"parse.warnings={warnings}")
    check.__name__ = "warns_on_unknown_input"
    return check


def top_mood_matches_or_neighbors(wanted_mood: str) -> Criterion:
    from src.recommender import _MOOD_NEIGHBORS

    def check(r: AgentResult) -> Tuple[bool, str]:
        if not r.recommendations:
            return False, "no recommendations"
        actual = r.recommendations[0][0]["mood"]
        allowed = {wanted_mood} | _MOOD_NEIGHBORS.get(wanted_mood, set())
        return (actual in allowed, f"top-mood='{actual}', allowed={sorted(allowed)}")
    check.__name__ = f"top_mood_matches_or_neighbors_{wanted_mood}"
    return check


def iterations_bounded(max_iters: int) -> Criterion:
    def check(r: AgentResult) -> Tuple[bool, str]:
        return (r.iterations <= max_iters,
                f"iterations={r.iterations}, max={max_iters}")
    check.__name__ = f"iterations_bounded_{max_iters}"
    return check


# ---------- Test cases ---------------------------------------------

@dataclass
class TestCase:
    name: str
    query: str
    criteria: List[Criterion]


TEST_CASES: List[TestCase] = [
    TestCase(
        name="clear-lofi-study-request",
        query="I want chill lofi music for studying with acoustic textures",
        criteria=[
            top_genre_in({"lofi", "jazz", "ambient"}),
            confidence_at_least("MEDIUM"),
            no_errors_or_crashes(),
            iterations_bounded(3),
        ],
    ),
    TestCase(
        name="high-energy-workout-pop",
        query="high energy pop for my workout, upbeat and electric",
        criteria=[
            top_genre_in({"pop", "indie pop", "edm", "synthwave"}),
            confidence_at_least("MEDIUM"),
            top_mood_matches_or_neighbors("energetic"),
            no_errors_or_crashes(),
        ],
    ),
    TestCase(
        name="intense-rock-request",
        query="intense rock, driving and powerful",
        criteria=[
            top_genre_in({"rock", "metal"}),
            no_errors_or_crashes(),
        ],
    ),
    TestCase(
        name="melancholy-classical-piano",
        query="melancholy classical piano, low energy",
        criteria=[
            top_genre_in({"classical", "ambient", "lofi"}),
            no_errors_or_crashes(),
        ],
    ),
    TestCase(
        name="unknown-genre-graceful-fallback",
        query="I want some k-pop hits with high energy",
        criteria=[
            warns_on_unknown_input(),
            no_errors_or_crashes(),
            iterations_bounded(3),
        ],
    ),
    TestCase(
        name="empty-query-does-not-crash",
        query="",
        criteria=[
            no_errors_or_crashes(),
            iterations_bounded(3),
        ],
    ),
]


# ---------- Runner --------------------------------------------------

@dataclass
class CriterionResult:
    name: str
    passed: bool
    detail: str


@dataclass
class CaseResult:
    name: str
    query: str
    criteria: List[CriterionResult]
    agent_result: AgentResult

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.criteria)


@dataclass
class EvaluationReport:
    cases: List[CaseResult] = field(default_factory=list)

    @property
    def n_total(self) -> int:
        return sum(len(c.criteria) for c in self.cases)

    @property
    def n_passed(self) -> int:
        return sum(1 for case in self.cases for c in case.criteria if c.passed)

    @property
    def n_cases_passed(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    def as_markdown(self) -> str:
        lines: List[str] = []
        lines.append("# Reliability Evaluation Report")
        lines.append("")
        lines.append(
            f"**Overall:** {self.n_cases_passed} / {len(self.cases)} cases passed, "
            f"{self.n_passed} / {self.n_total} individual criteria passed."
        )
        lines.append("")
        lines.append("| Case | Query | Criterion | Result | Detail |")
        lines.append("|---|---|---|---|---|")
        for case in self.cases:
            for i, c in enumerate(case.criteria):
                case_name = case.name if i == 0 else ""
                query = f"`{case.query}`" if i == 0 else ""
                mark = "✅ Pass" if c.passed else "❌ Fail"
                lines.append(f"| {case_name} | {query} | `{c.name}` | {mark} | {c.detail} |")
        lines.append("")
        lines.append("## Per-case agent trace summary")
        lines.append("")
        for case in self.cases:
            lines.append(f"### {case.name}")
            lines.append("")
            lines.append("```")
            lines.append(case.agent_result.summary())
            lines.append("```")
            lines.append("")
        return "\n".join(lines)

    def as_json(self) -> str:
        payload = {
            "summary": {
                "cases_passed": self.n_cases_passed,
                "cases_total": len(self.cases),
                "criteria_passed": self.n_passed,
                "criteria_total": self.n_total,
            },
            "cases": [
                {
                    "name": c.name,
                    "query": c.query,
                    "iterations": c.agent_result.iterations,
                    "mode_used": c.agent_result.mode_used,
                    "diversity_used": c.agent_result.diversity_used,
                    "aggregate_confidence": c.agent_result.critique.aggregate_confidence,
                    "confidence_label": c.agent_result.critique.confidence_label,
                    "criteria": [
                        {"name": r.name, "passed": r.passed, "detail": r.detail}
                        for r in c.criteria
                    ],
                }
                for c in self.cases
            ],
        }
        return json.dumps(payload, indent=2)


def run_evaluation(
    songs_path: str = "data/songs.csv",
    cases: List[TestCase] | None = None,
) -> EvaluationReport:
    songs = load_songs(songs_path)
    agent = RecommendationAgent(songs)
    cases = cases or TEST_CASES

    report = EvaluationReport()
    for case in cases:
        result = agent.run(case.query, k=5, run_id=case.name)
        criterion_results = []
        for criterion in case.criteria:
            passed, detail = criterion(result)
            criterion_results.append(
                CriterionResult(name=criterion.__name__, passed=passed, detail=detail)
            )
        report.cases.append(CaseResult(
            name=case.name,
            query=case.query,
            criteria=criterion_results,
            agent_result=result,
        ))
    return report


def write_reports(
    report: EvaluationReport,
    md_path: str = "evaluation_report.md",
    json_path: str = "evaluation_report.json",
) -> None:
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report.as_markdown())
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report.as_json())


if __name__ == "__main__":  # pragma: no cover
    r = run_evaluation()
    write_reports(r)
    print(f"cases passed: {r.n_cases_passed}/{len(r.cases)}, "
          f"criteria passed: {r.n_passed}/{r.n_total}")

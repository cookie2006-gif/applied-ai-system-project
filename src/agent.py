"""
Recommendation agent — orchestrates the plan → act → critique → refine loop.

Public API:
    RecommendationAgent(songs).run(query="I want chill music for studying", k=5)
        → AgentResult(profile, recommendations, critique, iterations, log)

The agent is deterministic. Every decision it makes (which mode to use,
whether to re-run with diversity, when to stop iterating) is derived from
the critic's structured findings. There is no LLM call, no randomness, and
no unbounded loop — the refine step is capped at MAX_ITERATIONS and each
remediation code can only fire once per run.

The point of this layer is to demonstrate an agentic workflow — "plan, act,
check its own work" — over a rules-based scoring engine. It's not a wrapper
around an LLM; it's a self-correcting pipeline that inspects its own output
and adjusts the strategy when the output falls short.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.critic import CritiqueReport, critique
from src.logger import RunLog
from src.query_parser import ParseResult, parse_query
from src.recommender import (
    SCORING_MODES,
    format_recommendations_table,
    recommend_songs,
)


MAX_ITERATIONS = 3


@dataclass
class AgentResult:
    query: str
    parse: ParseResult
    recommendations: List[Tuple[Dict, float, str]]
    critique: CritiqueReport
    iterations: int
    mode_used: str
    diversity_used: bool
    log: RunLog

    def summary(self) -> str:
        """Return a human-readable one-block summary of the whole run."""
        lines = []
        lines.append(f"Query: {self.query!r}")
        lines.append(f"Parsed profile: {self.parse.profile}")
        if self.parse.warnings:
            for w in self.parse.warnings:
                lines.append(f"  WARN: {w}")
        lines.append(
            f"Ran {self.iterations} iteration(s), mode={self.mode_used}, "
            f"diversity={self.diversity_used}"
        )
        lines.append(
            f"Aggregate confidence: {self.critique.aggregate_confidence:.2f} "
            f"({self.critique.confidence_label})"
        )
        if self.critique.findings:
            lines.append("Critic findings:")
            for f in self.critique.findings:
                lines.append(f"  [{f.severity.upper()}] {f.code}: {f.message}")
        lines.append("")
        lines.append(format_recommendations_table(self.recommendations))
        return "\n".join(lines)


class RecommendationAgent:
    """Wraps `recommend_songs` with a plan → critique → refine control loop."""

    def __init__(self, songs: List[Dict], max_iterations: int = MAX_ITERATIONS):
        if not songs:
            raise ValueError("agent cannot be constructed with an empty catalog")
        self.songs = songs
        self.max_iterations = max_iterations

    # ---- Planner --------------------------------------------------

    def _plan(self, query: str, log: RunLog) -> Tuple[ParseResult, str, bool]:
        """
        Turn the natural-language query into (profile, initial_mode, diversity).

        The initial mode is chosen from the parse result:
        - if the parser found a strong genre AND mood match → 'balanced'
        - if only mood matched → 'mood-first'
        - if only energy-context matched → 'energy-focused'
        - otherwise → 'balanced' with a warning
        """
        parse = parse_query(query)
        log.event(
            "plan.parse",
            matched=parse.matched_chunks,
            warnings=parse.warnings,
        )

        has_genre = "genre" in parse.matched_chunks
        has_mood = "mood" in parse.matched_chunks
        has_energy = "energy" in parse.matched_chunks

        if has_genre and has_mood:
            mode = "balanced"
        elif has_mood and not has_genre:
            mode = "mood-first"
        elif has_energy and not has_mood and not has_genre:
            mode = "energy-focused"
        else:
            mode = "balanced"

        diversity = False
        log.event("plan.strategy", mode=mode, diversity=diversity,
                  has_genre=has_genre, has_mood=has_mood, has_energy=has_energy)
        return parse, mode, diversity

    # ---- Act ------------------------------------------------------

    def _recommend(
        self,
        profile: Dict[str, Any],
        mode: str,
        diversity: bool,
        k: int,
        log: RunLog,
    ) -> List[Tuple[Dict, float, str]]:
        recs = recommend_songs(profile, self.songs, k=k, mode=mode, diversity=diversity)
        log.event(
            "act.recommend",
            mode=mode,
            diversity=diversity,
            returned=len(recs),
            top_song=recs[0][0]["title"] if recs else None,
            top_score=round(recs[0][1], 3) if recs else None,
        )
        return recs

    # ---- Critique -------------------------------------------------

    def _critique(
        self,
        recs: List[Tuple[Dict, float, str]],
        profile: Dict[str, Any],
        parse_warnings: List[str],
        diversity_on: bool,
        log: RunLog,
    ) -> CritiqueReport:
        report = critique(recs, profile, parse_warnings, diversity_on=diversity_on)
        log.event(
            "critique.report",
            aggregate=report.aggregate_confidence,
            label=report.confidence_label,
            finding_codes=report.codes(),
        )
        return report

    # ---- Refine ---------------------------------------------------

    def _refine(
        self,
        report: CritiqueReport,
        mode: str,
        diversity: bool,
        already_tried: set,
        log: RunLog,
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Pick the highest-severity actionable finding we haven't handled yet and
        translate it into a strategy change. Returns (new_mode, new_diversity,
        reason). Reason=None means nothing to refine.
        """
        priority = ["critical", "warn", "info"]
        for level in priority:
            for finding in report.findings:
                if finding.severity != level:
                    continue
                if finding.code in already_tried:
                    continue
                if finding.code == "TOP_MOOD_MISMATCH" and "mood-first" not in already_tried:
                    log.event("refine.decide", action="switch_mode", to="mood-first",
                              driver=finding.code)
                    return "mood-first", diversity, finding.code
                if finding.code == "LOW_AGGREGATE_CONFIDENCE" and "energy-focused" not in already_tried:
                    log.event("refine.decide", action="switch_mode", to="energy-focused",
                              driver=finding.code)
                    return "energy-focused", diversity, finding.code
                if finding.code == "ARTIST_REPETITION" and not diversity:
                    log.event("refine.decide", action="enable_diversity", driver=finding.code)
                    return mode, True, finding.code
        return mode, diversity, None

    # ---- Public entry point --------------------------------------

    def run(self, query: str, k: int = 5, run_id: Optional[str] = None) -> AgentResult:
        run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        log = RunLog(run_id=run_id)
        log.event("agent.start", query=query, k=k)

        parse, mode, diversity = self._plan(query, log)
        profile = parse.profile

        recs: List[Tuple[Dict, float, str]] = []
        report = CritiqueReport()
        already_tried: set = set()
        iterations = 0

        for i in range(self.max_iterations):
            iterations = i + 1
            log.event("iteration.start", n=iterations, mode=mode, diversity=diversity)
            recs = self._recommend(profile, mode, diversity, k, log)
            report = self._critique(recs, profile, parse.warnings, diversity, log)

            new_mode, new_diversity, driver = self._refine(
                report, mode, diversity, already_tried, log
            )
            if driver is None:
                log.event("iteration.stop", reason="no actionable findings")
                break

            already_tried.add(driver)
            if new_mode != mode:
                already_tried.add(new_mode)
            mode, diversity = new_mode, new_diversity

        log.event("agent.done", iterations=iterations, mode=mode, diversity=diversity,
                  aggregate=report.aggregate_confidence, label=report.confidence_label)

        return AgentResult(
            query=query,
            parse=parse,
            recommendations=recs,
            critique=report,
            iterations=iterations,
            mode_used=mode,
            diversity_used=diversity,
            log=log,
        )

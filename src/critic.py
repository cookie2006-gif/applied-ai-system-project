"""
Critic — inspects a candidate top-K list and returns structured findings.

Design contract:
- Deterministic. No LLM calls, no randomness. Same inputs → same findings.
- Findings are typed (severity + code + message) so the refiner can react
  programmatically rather than string-matching messages.
- Confidence is scored per-song and aggregated over the list. Numbers are
  bounded to [0, 1] so downstream reporting is stable.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


# Rough score ceilings observed empirically from the recipe. Used to
# normalize raw additive scores into a [0, 1] confidence per song.
# 2.0 (genre) + 1.0 (mood) + 2.0 (energy) + 1.0 (acoustic) + 0.5 (vibe)
# + 0.5 (popularity) + 0.5 (decade) + 1.0 (tags) + 0.5 (instr) + 0.25 (lang)
_MAX_POSSIBLE_SCORE = 8.75


@dataclass
class Finding:
    code: str
    severity: str          # 'info' | 'warn' | 'critical'
    message: str
    remediation: str = ""  # a hint the refiner can act on


@dataclass
class CritiqueReport:
    findings: List[Finding] = field(default_factory=list)
    per_song_confidence: List[float] = field(default_factory=list)
    aggregate_confidence: float = 0.0
    confidence_label: str = "LOW"

    def has_severity(self, level: str) -> bool:
        return any(f.severity == level for f in self.findings)

    def codes(self) -> List[str]:
        return [f.code for f in self.findings]


def _label(agg: float) -> str:
    if agg >= 0.75:
        return "HIGH"
    if agg >= 0.5:
        return "MEDIUM"
    return "LOW"


def per_song_confidence(score: float) -> float:
    """Normalize a raw additive score to [0, 1]."""
    return max(0.0, min(1.0, score / _MAX_POSSIBLE_SCORE))


def critique(
    recommendations: List[Tuple[Dict, float, str]],
    user_prefs: Dict[str, Any],
    parse_warnings: List[str] | None = None,
    diversity_on: bool = False,
) -> CritiqueReport:
    """
    Score the current top-K list and emit findings for anything the refiner
    should reconsider.

    Checks:
      1. Aggregate confidence too low → suggest energy-focused mode fallback.
      2. Top result's mood contradicts the requested mood → suggest mood-first.
      3. Artist repetition in top-K → suggest diversity=True.
      4. Score-flatness (top and #5 within 0.5 pts) → warn, no auto-fix.
      5. Unknown-genre parse warning → downgrade confidence label ceiling.
    """
    report = CritiqueReport()
    parse_warnings = parse_warnings or []

    if not recommendations:
        report.findings.append(Finding(
            code="EMPTY_RESULTS",
            severity="critical",
            message="the recommender returned zero songs — catalog may be empty",
        ))
        report.confidence_label = "LOW"
        return report

    # Per-song confidence
    confidences = [per_song_confidence(score) for _, score, _ in recommendations]
    report.per_song_confidence = confidences
    report.aggregate_confidence = round(statistics.mean(confidences), 3)

    # Check 1: aggregate too low
    if report.aggregate_confidence < 0.35:
        report.findings.append(Finding(
            code="LOW_AGGREGATE_CONFIDENCE",
            severity="warn",
            message=f"average confidence {report.aggregate_confidence:.2f} is low",
            remediation="switch to energy-focused mode (drops picky genre/mood filters)",
        ))

    # Check 2: top result's mood contradicts requested mood
    wanted_mood = user_prefs.get("mood") or user_prefs.get("favorite_mood")
    top_song = recommendations[0][0]
    top_mood = top_song.get("mood", "")
    if wanted_mood and top_mood and top_mood != wanted_mood:
        from src.recommender import _MOOD_NEIGHBORS  # local import to avoid cycles at load
        if top_mood not in _MOOD_NEIGHBORS.get(wanted_mood, set()):
            report.findings.append(Finding(
                code="TOP_MOOD_MISMATCH",
                severity="warn",
                message=(
                    f"top pick's mood is '{top_mood}' but the user asked for "
                    f"'{wanted_mood}' — genre weight is over-driving the ranking"
                ),
                remediation="switch to mood-first mode",
            ))

    # Check 3: artist repetition in top-K
    artists = [s.get("artist", "") for s, _, _ in recommendations]
    duplicates = {a for a in artists if artists.count(a) > 1 and a}
    if duplicates and not diversity_on:
        report.findings.append(Finding(
            code="ARTIST_REPETITION",
            severity="info",
            message=f"top-K contains repeated artist(s): {sorted(duplicates)}",
            remediation="enable diversity re-ranker",
        ))

    # Check 4: flat score curve
    top_score = recommendations[0][1]
    tail_score = recommendations[-1][1]
    if len(recommendations) >= 3 and (top_score - tail_score) < 0.5:
        report.findings.append(Finding(
            code="FLAT_SCORE_CURVE",
            severity="info",
            message=(
                f"top-K scores range from {top_score:.2f} to {tail_score:.2f} — "
                f"ranking difference between picks is smaller than the audible "
                f"difference between songs"
            ),
            remediation="",  # no auto-fix; flag for the human
        ))

    # Check 5: parse warnings downgrade confidence ceiling
    for w in parse_warnings:
        report.findings.append(Finding(
            code="PARSE_WARNING",
            severity="warn",
            message=w,
        ))

    # Compute label, but cap at MEDIUM if any parse warning fired
    label = _label(report.aggregate_confidence)
    if any(f.code == "PARSE_WARNING" for f in report.findings) and label == "HIGH":
        label = "MEDIUM"
    report.confidence_label = label
    return report

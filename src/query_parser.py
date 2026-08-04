"""
Natural-language → UserProfile parser (RAG-lite).

Loads the music-domain KB in `src/kb/music_terms.md`, indexes every
`- <value>   triggers: <keywords>` line by keyword, and maps a
free-form user query into the structured preference dict that the
scoring engine consumes.

This is a deterministic, dependency-free stand-in for an embedding-
based retriever. The important design points:

- Retrieval is a keyword match against the KB, not a hardcoded dict
  inside the code. If a curator wants to add "vaporwave → chillwave"
  they edit the .md file, not the parser.
- The parser reports which KB chunks fired for each field so the
  agent's critic can see *why* a field was populated (or wasn't) and
  can flag low-confidence parses to the user.
- Unknown genres do NOT crash the pipeline. They're captured as
  `warnings` on the parse result so the agent knows to fall back to
  mood + energy scoring.
"""

from __future__ import annotations

import os
import re
import string
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


KB_PATH = os.path.join(os.path.dirname(__file__), "kb", "music_terms.md")

# Punctuation to strip from token edges but NOT interiors — this preserves
# hyphens in tokens like "k-pop" or "lo-fi" so a "pop" trigger doesn't
# accidentally match "k-pop" via substring.
_EDGE_PUNCT = string.punctuation


# ---- Load and index the KB once at import time -----------------------

def _parse_kb(path: str) -> Dict[str, List[Tuple[str, List[str]]]]:
    """
    Return a mapping of field → list of (value, trigger-keywords).

    Only lines inside ```kb ... ``` fenced blocks are read; every other
    line in music_terms.md is treated as prose commentary.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks: Dict[str, List[Tuple[str, List[str]]]] = {}
    for block in re.findall(r"```kb\n(.*?)```", text, flags=re.DOTALL):
        field_line = re.search(r"field:\s*(\S+)", block)
        if not field_line:
            continue
        field_name = field_line.group(1)
        entries: List[Tuple[str, List[str]]] = []
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("- "):
                continue
            match = re.match(r"-\s+(\S(?:.*?\S)?)\s+triggers:\s*(.*)$", line)
            if not match:
                continue
            value = match.group(1).strip()
            triggers = [t.strip().lower() for t in match.group(2).split(",") if t.strip()]
            entries.append((value, triggers))
        chunks[field_name] = entries
    return chunks


_KB_CHUNKS: Dict[str, List[Tuple[str, List[str]]]] = _parse_kb(KB_PATH)


# ---- Retrieval ------------------------------------------------------

@dataclass
class ParseResult:
    """Structured outcome of parsing a NL query."""
    profile: Dict = field(default_factory=dict)
    matched_chunks: Dict[str, str] = field(default_factory=dict)   # field → matched trigger
    warnings: List[str] = field(default_factory=list)
    raw_query: str = ""

    def as_reasons(self) -> List[str]:
        reasons = [f"{f}: matched '{t}' from KB" for f, t in self.matched_chunks.items()]
        reasons += [f"WARN: {w}" for w in self.warnings]
        return reasons


def _tokenize(query: str) -> set:
    """
    Break a query into whole-word tokens with edge punctuation stripped
    but interior hyphens preserved — so 'k-pop' stays a single token and
    a 'pop' trigger will not match it.
    """
    tokens = set()
    for raw in query.lower().split():
        stripped = raw.strip(_EDGE_PUNCT)
        if stripped:
            tokens.add(stripped)
    return tokens


def _find_field(query: str, field_name: str) -> Optional[Tuple[str, str]]:
    """
    Look up a field in the KB. Returns (value, matched-trigger) or None.

    - Single-word triggers must appear as a whole token in the query.
    - Multi-word triggers use padded-substring matching so 'high energy'
      only fires when those two words appear adjacently.
    - Longest-trigger-first ordering breaks ties, so 'lo fi' wins over 'lo'.
    """
    q_lower = query.lower()
    q_padded = " " + q_lower + " "
    q_tokens = _tokenize(query)

    all_entries = _KB_CHUNKS.get(field_name, [])
    candidates: List[Tuple[int, str, str]] = []
    for value, triggers in all_entries:
        for trigger in triggers:
            if trigger == "(default)":
                continue
            if " " in trigger:
                if " " + trigger + " " in q_padded:
                    candidates.append((len(trigger), value, trigger))
            else:
                if trigger in q_tokens:
                    candidates.append((len(trigger), value, trigger))
    if not candidates:
        return None
    candidates.sort(reverse=True)  # longest trigger wins
    _, value, trigger = candidates[0]
    return value, trigger


def parse_query(query: str) -> ParseResult:
    """
    Map a natural-language query to a UserProfile-shaped dict.

    Fields the parser tries to populate: genre, mood, energy, likes_acoustic,
    prefers_instrumental, extra_mood_tags, popularity_preference. Anything
    it can't infer stays absent from the profile (the recommender's defaults
    kick in) and a warning is added.
    """
    result = ParseResult(raw_query=query)
    if not query or not query.strip():
        result.warnings.append("empty query — falling back to a neutral profile")
        result.profile = {
            "genre": "pop", "mood": "chill", "energy": 0.5, "likes_acoustic": False,
        }
        return result

    # --- categorical fields ---
    for field_name, profile_key in [
        ("genre", "genre"),
        ("mood", "mood"),
        ("extra_mood_tags", "extra_mood_tags"),
        ("popularity_preference", "popularity_preference"),
    ]:
        hit = _find_field(query, field_name)
        if hit:
            value, trigger = hit
            result.profile[profile_key] = value
            result.matched_chunks[field_name] = trigger

    # --- energy is numeric ---
    energy_hit = _find_field(query, "energy")
    if energy_hit:
        value, trigger = energy_hit
        result.profile["energy"] = float(value)
        result.matched_chunks["energy"] = trigger

    # --- booleans (acoustic, instrumental) ---
    for field_name, profile_key in [
        ("likes_acoustic", "likes_acoustic"),
        ("prefers_instrumental", "prefers_instrumental"),
    ]:
        hit = _find_field(query, field_name)
        if hit:
            value, trigger = hit
            result.profile[profile_key] = (value.lower() == "true")
            result.matched_chunks[field_name] = trigger

    # --- guardrails / warnings ---
    if "genre" not in result.profile:
        result.warnings.append(
            "no genre matched the KB — the recommender will score on mood + energy only"
        )
        result.profile["genre"] = "__unknown__"

    if "mood" not in result.profile:
        result.warnings.append("no mood matched the KB — defaulting to 'chill'")
        result.profile["mood"] = "chill"

    if "energy" not in result.profile:
        result.warnings.append("no energy cue detected — defaulting to 0.5")
        result.profile["energy"] = 0.5

    if "likes_acoustic" not in result.profile:
        # Not a warning — it's a legitimately optional field, default False.
        result.profile["likes_acoustic"] = False

    return result

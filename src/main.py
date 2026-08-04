"""
Applied AI System — VibeMatch 2.0

Entry point for the agentic recommender. Sends a battery of natural-language
queries through the full pipeline (planner → recommender → critic → refiner)
and prints the trace + recommendations + confidence for each one.

    python -m src.main             # runs the demo (this file)
    python -m src.evaluation       # runs the reliability harness

The old points-only recommender lives in src/recommender.py and is still
used as the scoring core; this file just drives the agent that wraps it.
"""

from typing import List, Tuple

from src.agent import RecommendationAgent
from src.recommender import load_songs


DEMO_QUERIES: List[Tuple[str, str]] = [
    (
        "clear lofi study request",
        "I want chill lofi music for studying with acoustic textures",
    ),
    (
        "high-energy workout",
        "high energy pop for my workout, upbeat and electric",
    ),
    (
        "melancholy classical",
        "melancholy classical piano, low energy for reflection",
    ),
    (
        "unknown-genre fallback",
        "I want some k-pop hits with high energy",  # k-pop is not in the catalog
    ),
    (
        "diversity trigger — same-artist stack",
        "chill lofi",  # will produce two LoRoom songs → critic should ask for diversity
    ),
    (
        "empty query fallback",
        "",
    ),
]


def main() -> None:
    print("=" * 78)
    print("VibeMatch 2.0 — Applied AI Recommender (agent-driven)")
    print("=" * 78)

    songs = load_songs("data/songs.csv")
    print(f"Loaded catalog: {len(songs)} songs\n")

    agent = RecommendationAgent(songs)

    for i, (label, query) in enumerate(DEMO_QUERIES, start=1):
        print("=" * 78)
        print(f"[{i}/{len(DEMO_QUERIES)}] {label}")
        print("=" * 78)

        result = agent.run(query, k=5)
        print(result.summary())
        print()

        # Persist the structured trace for post-hoc inspection.
        log_path = result.log.flush_to_disk()

    print("=" * 78)
    print(f"Full JSONL trace written to: {log_path}")
    print("Run `python -m src.evaluation` to execute the reliability harness.")
    print("=" * 78)


if __name__ == "__main__":
    main()

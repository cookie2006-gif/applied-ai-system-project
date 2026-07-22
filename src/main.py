"""
Command line runner for the Music Recommender Simulation.

Demonstrates:
  - Challenge 1: 5 new song features (popularity, decade, mood_tags, instrumental, language)
  - Challenge 2: 4 scoring modes (balanced / genre-first / mood-first / energy-focused)
  - Challenge 3: diversity penalty for repeated artists / genres
  - Challenge 4: formatted ASCII table output with per-song reasons
"""

from typing import Dict, List, Tuple

from src.recommender import (
    load_songs,
    recommend_songs,
    format_recommendations_table,
    SCORING_MODES,
)


PROFILES: List[Tuple[str, Dict]] = [
    ("High-Energy Pop",
        {"genre": "pop", "mood": "happy", "energy": 0.85, "likes_acoustic": False,
         "popularity_preference": "popular", "preferred_decade": "2020s"}),
    ("Chill Lofi Study",
        {"genre": "lofi", "mood": "focused", "energy": 0.40, "likes_acoustic": True,
         "extra_mood_tags": "studying|calm|focused",
         "prefers_instrumental": True, "preferred_language": "instrumental"}),
    ("Deep Intense Rock",
        {"genre": "rock", "mood": "intense", "energy": 0.90, "likes_acoustic": False,
         "extra_mood_tags": "driving|adrenaline"}),
    ("Sad but Hyped (conflicting mood vs. energy)",
        {"genre": "indie pop", "mood": "melancholy", "energy": 0.90, "likes_acoustic": False}),
    ("Metalhead Who Wants Acoustic (conflicting genre vs. acoustic)",
        {"genre": "metal", "mood": "aggressive", "energy": 0.95, "likes_acoustic": True,
         "prefers_instrumental": False}),
    ("Unknown Genre (not in catalog or neighbor graph)",
        {"genre": "k-pop", "mood": "happy", "energy": 0.70, "likes_acoustic": False}),
]


def print_profile_header(label: str, prefs: Dict) -> None:
    """Print the persona name and its preference dict."""
    print("=" * 78)
    print(f"Profile: {label}")
    print("=" * 78)
    for key, value in prefs.items():
        print(f"  {key:<24}: {value}")


def print_mode_comparison(label: str, prefs: Dict, songs: List[Dict], k: int = 5) -> None:
    """Run each scoring mode against the profile and print a compact side-by-side."""
    print(f"\n--- {label}: top-{k} across scoring modes ---")
    columns: List[Tuple[str, List[str]]] = []
    for mode in SCORING_MODES:
        recs = recommend_songs(prefs, songs, k=k, mode=mode)
        lines = [f"{r+1}. {s['title']} ({s['genre']}) {score:.2f}"
                 for r, (s, score, _) in enumerate(recs)]
        columns.append((mode, lines))

    # Print header row
    header = "".join(f"{mode:<38}" for mode, _ in columns)
    print(header)
    print("-" * len(header))
    for row in range(k):
        line = ""
        for _, lines in columns:
            cell = lines[row] if row < len(lines) else ""
            line += f"{cell:<38}"
        print(line)


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    k = 5

    # --- Section A: full detailed output per profile in "balanced" mode with the table formatter ---
    print("#" * 78)
    print("# SECTION A — Full recommendations per profile (balanced mode, ASCII table)")
    print("#" * 78)
    for label, prefs in PROFILES:
        print()
        print_profile_header(label, prefs)
        recs = recommend_songs(prefs, songs, k=k, mode="balanced")
        print()
        print(format_recommendations_table(recs))

    # --- Section B: side-by-side comparison of scoring modes for one profile ---
    print("\n" + "#" * 78)
    print("# SECTION B — Scoring-mode comparison for 'High-Energy Pop'")
    print("#" * 78)
    label, prefs = PROFILES[0]
    print_mode_comparison(label, prefs, songs, k=k)

    # --- Section C: diversity penalty on / off for 'Chill Lofi Study' ---
    print("\n" + "#" * 78)
    print("# SECTION C — Diversity penalty ON vs OFF for 'Chill Lofi Study'")
    print("#" * 78)
    label, prefs = PROFILES[1]
    for diversity in (False, True):
        state = "ON" if diversity else "OFF"
        print(f"\n--- Diversity {state} ---")
        recs = recommend_songs(prefs, songs, k=k, diversity=diversity)
        print(format_recommendations_table(recs))


if __name__ == "__main__":
    main()

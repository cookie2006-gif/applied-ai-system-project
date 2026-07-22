import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

    # ---- Advanced attributes (Challenge 1) ----
    # All new fields have defaults so existing tests (which construct
    # Song with just the original ten fields) keep passing.
    popularity: int = 50
    release_decade: str = "2020s"
    mood_tags: str = ""          # pipe-separated, e.g. "focused|dreamy"
    instrumental: bool = False
    language: str = "en"


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

    # ---- Advanced preferences (Challenge 1) ----
    popularity_preference: str = "any"          # 'popular' | 'obscure' | 'any'
    preferred_decade: Optional[str] = None       # e.g. "2020s"
    extra_mood_tags: str = ""                    # pipe-separated, matches Song.mood_tags
    prefers_instrumental: Optional[bool] = None  # None = don't care
    preferred_language: Optional[str] = None     # e.g. "en", "instrumental"


# Neighbor lookups let a close-but-not-exact genre/mood earn partial credit
# instead of getting a 0. Symmetry is enforced by _neighbors().
_GENRE_NEIGHBORS: Dict[str, set] = {
    "lofi": {"jazz", "ambient", "classical"},
    "jazz": {"lofi", "ambient", "r&b"},
    "ambient": {"lofi", "jazz", "classical"},
    "classical": {"ambient", "lofi"},
    "pop": {"indie pop", "synthwave", "edm"},
    "indie pop": {"pop", "synthwave"},
    "synthwave": {"pop", "indie pop", "edm"},
    "edm": {"pop", "synthwave"},
    "rock": {"metal"},
    "metal": {"rock"},
    "hip hop": {"r&b"},
    "r&b": {"hip hop", "jazz"},
    "folk": {"country"},
    "country": {"folk"},
}

_MOOD_NEIGHBORS: Dict[str, set] = {
    "chill": {"relaxed", "focused"},
    "relaxed": {"chill", "focused", "romantic"},
    "focused": {"chill", "relaxed"},
    "happy": {"hopeful", "euphoric"},
    "hopeful": {"happy", "relaxed"},
    "euphoric": {"happy", "energetic"},
    "intense": {"aggressive", "energetic", "moody"},
    "aggressive": {"intense", "energetic"},
    "energetic": {"intense", "euphoric", "aggressive"},
    "moody": {"melancholy", "wistful", "intense"},
    "melancholy": {"moody", "wistful", "nostalgic"},
    "wistful": {"moody", "melancholy", "nostalgic"},
    "nostalgic": {"wistful", "melancholy"},
    "romantic": {"relaxed", "moody"},
}

# Vibe bonus (danceability + valence) only helps users in upbeat moods.
_VIBE_MOODS = {"happy", "relaxed", "euphoric", "hopeful"}


# ============================================================
# Scoring modes (Challenge 2) — Strategy pattern via weight dicts
# ============================================================
#
# Each mode is a dict of multipliers applied to the base recipe's
# per-component point ceilings. Multiplier 1.0 = no change from base;
# 0.5 = half weight; 2.0 = double weight. This keeps the scoring
# code centralized and lets new modes be added in one line.

BASELINE_MODE = {
    "genre": 1.0, "mood": 1.0, "energy": 1.0,
    "acoustic": 1.0, "vibe": 1.0,
    "popularity": 1.0, "decade": 1.0,
    "tags": 1.0, "instrumental": 1.0, "language": 1.0,
}

SCORING_MODES: Dict[str, Dict[str, float]] = {
    "balanced": BASELINE_MODE,
    "genre-first": {**BASELINE_MODE, "genre": 2.0, "energy": 0.5},
    "mood-first": {**BASELINE_MODE, "mood": 3.0, "tags": 2.0, "genre": 0.5},
    "energy-focused": {**BASELINE_MODE, "energy": 2.5, "genre": 0.5, "mood": 0.5},
}


def _neighbors(table: Dict[str, set], key: str) -> set:
    """Return the neighbor set for a categorical key, or an empty set if unknown."""
    return table.get(key, set())


def _parse_tags(raw: str) -> set:
    """Split a pipe-separated mood-tags string into a set of trimmed lowercase tags."""
    if not raw:
        return set()
    return {t.strip().lower() for t in raw.split("|") if t.strip()}


def _score_components(
    song: Dict,
    user: Dict,
    mode: Dict[str, float] = BASELINE_MODE,
) -> Tuple[float, List[str]]:
    """
    Core scoring routine. Accepts song + user as dicts and returns
    (total_score, reasons). Weights are scaled by `mode`, a dict of
    per-component multipliers (see SCORING_MODES). Used by both the
    dict-based score_song() and the OOP Recommender._score().
    """
    reasons: List[str] = []
    total = 0.0

    fav_genre = user["favorite_genre"]
    fav_mood = user["favorite_mood"]
    target_energy = float(user["target_energy"])
    likes_acoustic = bool(user.get("likes_acoustic", False))

    song_genre = song["genre"]
    song_mood = song["mood"]
    song_energy = float(song["energy"])
    song_valence = float(song["valence"])
    song_danceability = float(song["danceability"])
    song_acousticness = float(song["acousticness"])

    # --- Genre: +2.0 exact, +1.0 neighbor ---
    if song_genre == fav_genre:
        pts = 2.0 * mode["genre"]
        total += pts
        reasons.append(f"matched genre ({song_genre}) [+{pts:.2f}]")
    elif song_genre in _neighbors(_GENRE_NEIGHBORS, fav_genre):
        pts = 1.0 * mode["genre"]
        total += pts
        reasons.append(f"related genre ({song_genre} ~ {fav_genre}) [+{pts:.2f}]")

    # --- Mood: +1.0 exact, +0.5 neighbor ---
    if song_mood == fav_mood:
        pts = 1.0 * mode["mood"]
        total += pts
        reasons.append(f"matched mood ({song_mood}) [+{pts:.2f}]")
    elif song_mood in _neighbors(_MOOD_NEIGHBORS, fav_mood):
        pts = 0.5 * mode["mood"]
        total += pts
        reasons.append(f"related mood ({song_mood} ~ {fav_mood}) [+{pts:.2f}]")

    # --- Energy: closeness, up to 2.0 ---
    energy_fit = max(0.0, 1.0 - abs(song_energy - target_energy))
    pts = 2.0 * energy_fit * mode["energy"]
    if pts >= 0.05:
        total += pts
        reasons.append(
            f"energy {song_energy:.2f} vs target {target_energy:.2f} [+{pts:.2f}]"
        )

    # --- Acoustic: up to 1.0 ---
    acoustic_fit = song_acousticness if likes_acoustic else (1.0 - song_acousticness)
    pts = 1.0 * acoustic_fit * mode["acoustic"]
    if pts >= 0.05:
        total += pts
        label = "acoustic-forward" if likes_acoustic else "produced/electric"
        reasons.append(f"{label} texture [+{pts:.2f}]")

    # --- Vibe bonus (conditional): up to 0.5 ---
    if fav_mood in _VIBE_MOODS:
        pts = 0.5 * (0.5 * song_valence + 0.5 * song_danceability) * mode["vibe"]
        if pts >= 0.05:
            total += pts
            reasons.append(
                f"upbeat vibe (v={song_valence:.2f}, d={song_danceability:.2f}) [+{pts:.2f}]"
            )

    # --- Popularity: up to 0.5, based on user preference ---
    popularity = float(song.get("popularity", 50)) / 100.0
    pref = user.get("popularity_preference", "any")
    pop_fit = 0.0
    if pref == "popular":
        pop_fit = popularity
    elif pref == "obscure":
        pop_fit = 1.0 - popularity
    pts = 0.5 * pop_fit * mode["popularity"]
    if pts >= 0.05:
        total += pts
        reasons.append(f"{pref} taste (pop={int(popularity*100)}) [+{pts:.2f}]")

    # --- Release decade: +0.5 exact match ---
    pref_decade = user.get("preferred_decade")
    song_decade = song.get("release_decade", "")
    if pref_decade and song_decade == pref_decade:
        pts = 0.5 * mode["decade"]
        total += pts
        reasons.append(f"matched decade ({song_decade}) [+{pts:.2f}]")

    # --- Mood tags: +0.25 per matching tag, up to 1.0 ---
    user_tags = _parse_tags(user.get("extra_mood_tags", ""))
    song_tags = _parse_tags(song.get("mood_tags", ""))
    overlap = user_tags & song_tags
    if overlap:
        raw_pts = min(1.0, 0.25 * len(overlap))
        pts = raw_pts * mode["tags"]
        total += pts
        reasons.append(f"mood tags {sorted(overlap)} [+{pts:.2f}]")

    # --- Instrumental preference: +0.5 if matches, -0.25 if clashes ---
    prefers_instr = user.get("prefers_instrumental")
    song_instr = bool(song.get("instrumental", False))
    if prefers_instr is not None:
        if prefers_instr == song_instr:
            pts = 0.5 * mode["instrumental"]
            total += pts
            label = "instrumental match" if song_instr else "has vocals as preferred"
            reasons.append(f"{label} [+{pts:.2f}]")
        else:
            pts = -0.25 * mode["instrumental"]
            total += pts
            label = "wanted instrumental" if prefers_instr else "wanted vocals"
            reasons.append(f"{label}, got the opposite [{pts:.2f}]")

    # --- Language: +0.25 exact match ---
    pref_lang = user.get("preferred_language")
    song_lang = song.get("language", "")
    if pref_lang and song_lang == pref_lang:
        pts = 0.25 * mode["language"]
        total += pts
        reasons.append(f"matched language ({song_lang}) [+{pts:.2f}]")

    return total, reasons


def _tiebreak_key(song_genre: str, fav_genre: str, energy_points: float, song_id: int) -> Tuple:
    """Build the tie-break tuple: prefer stronger genre match, then higher energy, then lower id."""
    genre_rank = 2 if song_genre == fav_genre else (1 if song_genre in _neighbors(_GENRE_NEIGHBORS, fav_genre) else 0)
    return (-genre_rank, -energy_points, song_id)


def _apply_diversity_penalty(
    ranked: List[Tuple[float, Tuple, Dict, List[str]]],
    k: int,
    artist_penalty: float = 0.75,
    genre_penalty: float = 0.30,
) -> List[Tuple[float, Tuple, Dict, List[str]]]:
    """
    Challenge 3: re-rank a scored list by penalizing songs whose artist or
    genre has already appeared in the top-k selection so far.

    Walks the list highest-first, greedily picks the best remaining song,
    then subtracts artist_penalty / genre_penalty from every remaining
    candidate that shares the same artist / genre. Repeats until k are
    picked. Modifies scores in-place (on a copy), so the "final" score
    each song shows reflects any penalty it took.
    """
    picked: List[Tuple[float, Tuple, Dict, List[str]]] = []
    seen_artists: Dict[str, int] = {}
    seen_genres: Dict[str, int] = {}

    # Work on a mutable copy of the list of lists so we can adjust scores.
    remaining = [(s, tb, song, list(reasons)) for (s, tb, song, reasons) in ranked]

    for _ in range(min(k, len(remaining))):
        remaining.sort(key=lambda row: (-row[0],) + row[1])
        best_score, best_tb, best_song, best_reasons = remaining.pop(0)
        picked.append((best_score, best_tb, best_song, best_reasons))
        seen_artists[best_song["artist"]] = seen_artists.get(best_song["artist"], 0) + 1
        seen_genres[best_song["genre"]] = seen_genres.get(best_song["genre"], 0) + 1

        # Penalize every remaining candidate that repeats artist/genre.
        for i, (score, tb, song, reasons) in enumerate(remaining):
            deduction = 0.0
            notes: List[str] = []
            if song["artist"] in seen_artists:
                deduction += artist_penalty * seen_artists[song["artist"]]
                notes.append(f"artist repeat [-{artist_penalty * seen_artists[song['artist']]:.2f}]")
            if song["genre"] in seen_genres:
                # Only start penalizing genre after the SECOND song in that genre.
                repeats = seen_genres[song["genre"]]
                if repeats >= 2:
                    penalty = genre_penalty * (repeats - 1)
                    deduction += penalty
                    notes.append(f"genre repeat [-{penalty:.2f}]")
            if deduction > 0:
                remaining[i] = (score - deduction, tb, song, reasons + notes)

    return picked


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _song_to_dict(self, song: Song) -> Dict:
        """Bridge from the Song dataclass to the dict shape used by _score_components."""
        return {
            "id": song.id, "title": song.title, "artist": song.artist,
            "genre": song.genre, "mood": song.mood,
            "energy": song.energy, "valence": song.valence,
            "danceability": song.danceability, "acousticness": song.acousticness,
            "popularity": song.popularity, "release_decade": song.release_decade,
            "mood_tags": song.mood_tags, "instrumental": song.instrumental,
            "language": song.language,
        }

    def _user_to_dict(self, user: UserProfile) -> Dict:
        """Bridge from the UserProfile dataclass to the dict shape used by _score_components."""
        return {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
            "popularity_preference": user.popularity_preference,
            "preferred_decade": user.preferred_decade,
            "extra_mood_tags": user.extra_mood_tags,
            "prefers_instrumental": user.prefers_instrumental,
            "preferred_language": user.preferred_language,
        }

    def _score(self, user: UserProfile, song: Song, mode: Dict[str, float] = BASELINE_MODE) -> Tuple[float, List[str]]:
        """Score a Song against a UserProfile using the shared scoring core."""
        return _score_components(self._song_to_dict(song), self._user_to_dict(user), mode)

    def recommend(self, user: UserProfile, k: int = 5, mode: str = "balanced", diversity: bool = False) -> List[Song]:
        """Return the top-k Songs ranked by score against the given UserProfile."""
        weights = SCORING_MODES.get(mode, BASELINE_MODE)
        scored = []
        for song in self.songs:
            score, reasons = self._score(user, song, weights)
            energy_points = 2.0 * max(0.0, 1.0 - abs(song.energy - user.target_energy))
            tb = _tiebreak_key(song.genre, user.favorite_genre, energy_points, song.id)
            scored.append((score, tb, self._song_to_dict(song), reasons))

        scored.sort(key=lambda row: (-row[0],) + row[1])
        top = _apply_diversity_penalty(scored, k) if diversity else scored[:k]

        # Rebuild Song objects for the caller by matching id back.
        by_id = {s.id: s for s in self.songs}
        return [by_id[row[2]["id"]] for row in top]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a one-line summary of the score and the reasons this Song was picked."""
        score, reasons = self._score(user, song)
        if not reasons:
            return f"No strong match (score {score:.2f})."
        return f"Score {score:.2f} — " + "; ".join(reasons) + "."


def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file into a list of dicts.
    Numeric columns are coerced to int/float; booleans parsed from "True"/"False".
    Required by src/main.py
    """
    numeric_int = {"id", "popularity"}
    numeric_float = {"energy", "tempo_bpm", "valence", "danceability", "acousticness"}
    boolean_cols = {"instrumental"}
    songs: List[Dict] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed: Dict = {}
            for key, value in row.items():
                if key in numeric_int:
                    parsed[key] = int(value)
                elif key in numeric_float:
                    parsed[key] = float(value)
                elif key in boolean_cols:
                    parsed[key] = value.strip().lower() == "true"
                else:
                    parsed[key] = value
            songs.append(parsed)

    return songs


def score_song(
    user_prefs: Dict,
    song: Dict,
    mode: str = "balanced",
) -> Tuple[float, List[str]]:
    """
    Scores a single song against a user_prefs dict.

    Expected user_prefs keys: "genre", "mood", "energy". Optional: "likes_acoustic",
    "popularity_preference", "preferred_decade", "extra_mood_tags",
    "prefers_instrumental", "preferred_language".
    Returns (score, reasons).
    """
    weights = SCORING_MODES.get(mode, BASELINE_MODE)
    # Translate the flat dict shape main.py uses ("genre") into the
    # canonical "favorite_genre" shape _score_components expects.
    user = {
        "favorite_genre": user_prefs["genre"],
        "favorite_mood": user_prefs["mood"],
        "target_energy": float(user_prefs["energy"]),
        "likes_acoustic": bool(user_prefs.get("likes_acoustic", False)),
        "popularity_preference": user_prefs.get("popularity_preference", "any"),
        "preferred_decade": user_prefs.get("preferred_decade"),
        "extra_mood_tags": user_prefs.get("extra_mood_tags", ""),
        "prefers_instrumental": user_prefs.get("prefers_instrumental"),
        "preferred_language": user_prefs.get("preferred_language"),
    }
    return _score_components(song, user, weights)


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    mode: str = "balanced",
    diversity: bool = False,
) -> List[Tuple[Dict, float, str]]:
    """
    Scores every song, sorts by score desc (with tie-breakers), returns top-k.
    Optional diversity=True applies the artist/genre repetition penalty.
    Each item: (song_dict, score, explanation_string).
    """
    scored: List[Tuple[float, Tuple, Dict, List[str]]] = []
    fav_genre = user_prefs["genre"]
    target_energy = float(user_prefs["energy"])

    for song in songs:
        score, reasons = score_song(user_prefs, song, mode=mode)
        energy_points = 2.0 * max(0.0, 1.0 - abs(float(song["energy"]) - target_energy))
        tb = _tiebreak_key(song["genre"], fav_genre, energy_points, int(song["id"]))
        scored.append((score, tb, song, reasons))

    scored.sort(key=lambda row: (-row[0],) + row[1])
    top = _apply_diversity_penalty(scored, k) if diversity else scored[:k]

    return [(row[2], row[0], "; ".join(row[3]) if row[3] else "no strong match") for row in top]


# ============================================================
# Challenge 4: Formatted table output
# ============================================================

def format_recommendations_table(
    recommendations: List[Tuple[Dict, float, str]],
    title_col_width: int = 22,
    artist_col_width: int = 16,
) -> str:
    """Render a top-k list as a two-row-per-song ASCII table with reasons underneath."""
    if not recommendations:
        return "(no recommendations)"

    # Header row
    header = f"{'#':<3}{'Title':<{title_col_width}}{'Artist':<{artist_col_width}}{'Genre':<11}{'Mood':<12}{'Score':>7}"
    sep = "-" * len(header)
    lines = [sep, header, sep]

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        title = (song["title"][:title_col_width - 1] + "…") if len(song["title"]) > title_col_width - 1 else song["title"]
        artist = (song["artist"][:artist_col_width - 1] + "…") if len(song["artist"]) > artist_col_width - 1 else song["artist"]
        lines.append(
            f"{rank:<3}{title:<{title_col_width}}{artist:<{artist_col_width}}"
            f"{song['genre']:<11}{song['mood']:<12}{score:>7.2f}"
        )
        # Reasons indented under the row
        reasons = explanation.split("; ") if explanation else ["no strong match"]
        for r in reasons:
            lines.append(f"     · {r}")
        lines.append("")

    lines.append(sep)
    return "\n".join(lines)

# AI Interactions Log

> Documentation of the stretch features and how I collaborated with Claude Code
> (Anthropic's Claude Opus 4.7 via the VS Code extension) to design and
> implement them.

---

## Agentic Workflow (SF8) — Challenge 1: Advanced Song Features

**What task did I give the agent?**

Extend the dataset and scoring engine to score songs on five new dimensions beyond the starter features (genre, mood, energy, acousticness, valence, danceability). Specifically: add `popularity` (0–100), `release_decade`, `mood_tags` (multi-tag descriptors), `instrumental` (bool), and `language` to every song in `data/songs.csv`, extend the `Song` and `UserProfile` dataclasses with matching optional preferences, teach `load_songs` to parse the new columns, and integrate them into `_score_components` so the additive score reflects them.

**Prompts I used (paraphrased from the actual chat):**

- *"Introduce 5+ complex attributes to the dataset that aren't currently present — Song Popularity, Release Decade, Mood Tags, etc. Update both `data/songs.csv` and the scoring logic in `src/recommender.py` so scoring accounts for the new attributes."*
- *"The new UserProfile fields need to be optional so the existing pytest cases (which construct UserProfile with only the original four fields) keep passing."*
- *"For `mood_tags`, use `|` as a separator inside CSV cells so commas don't confuse the parser."*
- *"For `instrumental`, the score should be `+0.5` when the user's preference matches the song, `-0.25` when it clashes, and `0` when the user doesn't care. Don't apply the penalty when `prefers_instrumental` is `None`."*

**What did the agent generate or change?**

- Rewrote [data/songs.csv](data/songs.csv) — added 5 new columns to the header and populated all 18 rows with hand-picked values (kept existing 10 columns unchanged).
- Extended the `Song` dataclass in [src/recommender.py](src/recommender.py) with `popularity`, `release_decade`, `mood_tags`, `instrumental`, `language` (all with defaults so tests still pass).
- Extended `UserProfile` with `popularity_preference`, `preferred_decade`, `extra_mood_tags`, `prefers_instrumental`, `preferred_language` (all with defaults).
- Rewrote `_score_components` to accept song + user as dicts (was previously flat args) so the extra fields could ride along without a 20-arg signature.
- Updated `load_songs` to parse the new columns — coerced `popularity` to `int`, parsed `instrumental` as a boolean from the string `"True"/"False"`, and left the rest as strings.
- Added five new scoring rules to `_score_components`: popularity fit (up to +0.5), decade match (+0.5), mood-tag overlap (+0.25 per matching tag, capped at +1.0), instrumental match (+0.5 or −0.25), language match (+0.25).

**What did I verify or fix manually?**

- **Field ordering in the dataclasses.** The agent initially put the new fields anywhere; I confirmed they landed *after* the required fields so Python's dataclass ordering rule (defaulted fields must follow non-defaulted ones) held.
- **Backwards compatibility with the tests.** Existing `test_recommender.py` constructs both `Song` and `UserProfile` with only the original fields. I ran `pytest -q` after the change and verified both cases still passed on the first try (the defaults on new fields are what kept them working).
- **Boolean CSV parsing.** The agent first suggested `bool(value)` for the `instrumental` column, which would evaluate `bool("False") == True` (non-empty string). I caught this and fixed it to `value.strip().lower() == "true"`.
- **Score accounting.** After the rewrite I ran `python -m src.main` and manually checked that the `Sunrise City` recommendation showed *all seven* firing components (five original + popularity + decade), that the point contributions summed correctly, and that a song with 0 popularity + wrong decade only earned points from the original components.

---

## Design Pattern (SF10) — Challenge 2: Multiple Scoring Modes

**Which design pattern did I use?**

**A lightweight Strategy pattern implemented as weight-multiplier dicts** rather than as a class hierarchy.

Each scoring mode is a dictionary of per-component multipliers keyed off a shared `BASELINE_MODE`:

```python
BASELINE_MODE = {"genre": 1.0, "mood": 1.0, "energy": 1.0, ...}

SCORING_MODES = {
    "balanced":       BASELINE_MODE,
    "genre-first":    {**BASELINE_MODE, "genre": 2.0, "energy": 0.5},
    "mood-first":     {**BASELINE_MODE, "mood": 3.0, "tags": 2.0, "genre": 0.5},
    "energy-focused": {**BASELINE_MODE, "energy": 2.5, "genre": 0.5, "mood": 0.5},
}
```

`_score_components(song, user, mode=BASELINE_MODE)` takes the mode dict and multiplies each component's base point value by the matching multiplier. Callers pass a mode *name* (e.g. `mode="mood-first"`), which is looked up in `SCORING_MODES` and defaults back to `"balanced"` if unrecognized.

**How did AI help me brainstorm or implement it?**

I described the goal in the chat: *"I want to switch scoring strategies at runtime — genre-first, mood-first, energy-focused, balanced. Suggest a design pattern that keeps recommender.py modular and lets new modes be added without editing the scoring function itself."*

The initial suggestion was a full **Strategy class hierarchy** — `ScoringStrategy` abstract base, `GenreFirstStrategy`, `MoodFirstStrategy`, etc. I pushed back: *"Each mode only differs in weights, not in behavior. A class per mode feels like overkill. Is there a way to keep the scoring code in one place and describe the modes as data?"*

The agent then proposed the weight-multiplier dict approach I ended up using. It's structurally a Strategy pattern (each mode is a distinct strategy that gets swapped in at call time) but the "strategies" are just data — no subclasses, no dispatch table, no boilerplate. New modes are one line of code.

**How does the pattern appear in the final code?**

- `SCORING_MODES` is the registry of available strategies ([recommender.py:106-111](src/recommender.py#L106-L111)).
- `_score_components(song, user, mode)` reads the multipliers and applies them inline ([recommender.py:127-247](src/recommender.py#L127-L247)).
- Callers pass `mode="..."`; `score_song`, `recommend_songs`, and `Recommender.recommend` all accept it and route it through.
- `main.py`'s Section B demonstrates it in action — the same profile is scored under all four modes side-by-side.

**Trade-off note.** This design works because every scoring difference between modes can be expressed as "component X is worth K times as much." If a mode ever needs *behavioral* differences (e.g. "in genre-first mode, ignore any song whose energy is more than 0.3 off the target"), the multiplier dict is no longer expressive enough — that's when the full class-based Strategy pattern would pay off.

---

## Challenge 3 — Diversity Penalty

**Prompt I used:**

> *"I want a rule that penalizes a song's score if its artist is already present in the top recommendations list. Walk through the ranked list highest-first, and for each song after the first, subtract points if its artist has already appeared. Genre repetition should also be penalized, but only starting from the third song in that genre — I want lofi to appear twice comfortably, not fifteen times."*

**How it's implemented.**

`_apply_diversity_penalty` in [recommender.py:253-292](src/recommender.py#L253-L292) does a greedy re-ranking pass. It picks the best-scoring remaining song, adds it to the "chosen" pile, then subtracts `artist_penalty` (0.75) from every remaining candidate that shares that artist, and `genre_penalty` (0.30) from every candidate that repeats the *already-picked-twice* genre. Then it re-sorts and picks again. Applied to `Chill Lofi Study`, this drops *Midnight Coding* (same artist "LoRoom" as *Focus Flow*) from position #2 and promotes *Library Rain* instead.

**Manual verification.** Ran both `diversity=False` and `diversity=True` back-to-back for the same profile and confirmed by eye that (a) the diversity-off list stacked two LoRoom songs at #1 and #2, and (b) the diversity-on list broke that up while still filling positions with reasonable lofi/lofi-adjacent picks.

---

## Challenge 4 — Formatted Table Output

**Prompt I used:**

> *"Improve the readability of the terminal output — show title, artist, genre, mood, and score in a table, and include the per-song 'reasons' underneath each row (not squeezed into a cell). Use plain ASCII formatting so we don't add a `tabulate` dependency."*

**How it's implemented.**

`format_recommendations_table` in [recommender.py:396-425](src/recommender.py#L396-L425) builds a header row, separator, and one row per recommendation, with each song's reasons rendered as bullet-indented lines directly under the row. Titles and artists are truncated with an ellipsis if they exceed the column width. No external libraries — just f-strings with column padding.

**Manual verification.** Ran `main.py` and confirmed:
- Column widths hold across all 6 personas, including the longest title *"Dust On The Dashboard"* (fits at width 22).
- Reasons wrap naturally as one-per-line under each row rather than colliding with the table.
- The output stays under 80 columns wide so it renders cleanly in a standard terminal.

---

## Meta-notes on the collaboration

Two patterns emerged consistently across these four challenges:

1. **The AI proposes bigger structure than needed.** For Challenge 2 the first suggestion was a full class hierarchy for what turned out to be a data-only difference between modes. Pushing back with "can we describe this as data?" led to a much smaller, more maintainable solution.
2. **AI is fast on scaffolding, slow on verification.** When the agent wrote the scoring rules or the CSV loader, I could accept the diff after a quick read. When it *predicted* what the output would look like ("this weight shift will push Gym Hero to #1"), the prediction turned out to be wrong — I had to actually run the code to know. The takeaway I keep coming back to: use the AI to generate code, but use the runtime to check behavior.

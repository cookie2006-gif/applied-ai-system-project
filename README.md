# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Real-world music recommenders like Spotify or Apple Music combine two big ideas: **content-based filtering** (looking at what a song *sounds like* — genre, tempo, audio features) and **collaborative filtering** (looking at what similar listeners liked). They also blend in context like time of day, listening history, and skip behavior, then re-rank the results for freshness and diversity so the same five songs don't play forever. My version is much smaller and only does the first half — it's a **content-based recommender** that compares each song's features (genre, mood, energy, valence, danceability, acousticness) against a simple `UserProfile` and scores how well they match. It prioritizes **closeness to the user's target energy**, **genre alignment**, and **acoustic preference**, using a weighted sum in `score_song`, then ranks the results in `recommend_songs` and returns the top-`k` with a short explanation of *why* each song was picked. The goal isn't to compete with Spotify — it's to make the scoring logic transparent enough that a person can read the output and understand exactly why a song showed up.

### Data flow

```
songs.csv ──► load_songs ──► list of Song dicts ─┐
                                                  ├──► score_song (per song) ──► (score, reasons)
UserProfile (genre, mood, energy, likes_acoustic)─┘                                         │
                                                                                            ▼
                                                                        sort by score desc  ─► top-K + explanations
                                                                        (tie-break: genre → energy → id)
```

### Song features used

- `genre`, `mood` — categorical, scored by exact / neighbor match.
- `energy` — numeric (0–1), scored by *closeness* to the user's target: `1 − |song.energy − target|`.
- `acousticness` — numeric (0–1), aligned to `likes_acoustic` (score = value, or `1 − value`).
- `valence`, `danceability` — power a small conditional "vibe bonus" for upbeat moods only.
- `tempo_bpm` — loaded but not scored (correlated with `energy` in this catalog, so it would double-count).

### UserProfile

Four fields, each mapped to one scoring component:

| Field | Type | Drives |
|---|---|---|
| `favorite_genre` | `str` | `genre_points` |
| `favorite_mood` | `str` | `mood_points` + toggles vibe bonus |
| `target_energy` | `float` (0–1) | `energy_points` |
| `likes_acoustic` | `bool` | `acoustic_points` (flips direction) |

### Finalized Algorithm Recipe

Each song gets an additive score. Max ≈ 6.5.

```
score(song, user) = genre_points + mood_points + energy_points + acoustic_points + vibe_bonus
```

| Component | Points | Rule |
|---|---|---|
| **Genre** | **+2.0** | exact match on `favorite_genre` |
| Genre neighbor | +1.0 | same family (e.g. `lofi ↔ jazz ↔ ambient ↔ classical`; `pop ↔ indie pop ↔ synthwave ↔ edm`; `rock ↔ metal`; `hip hop ↔ r&b`; `folk ↔ country`) |
| **Mood** | **+1.0** | exact match on `favorite_mood` |
| Mood neighbor | +0.5 | same family (e.g. `chill ↔ relaxed ↔ focused`; `happy ↔ hopeful ↔ euphoric`; `intense ↔ aggressive ↔ energetic`; `moody ↔ melancholy ↔ wistful ↔ nostalgic`) |
| **Energy** | **up to +2.0** | `2.0 × (1 − \|song.energy − target_energy\|)` — closeness, not magnitude |
| **Acoustic** | **up to +1.0** | `song.acousticness` if `likes_acoustic`, else `1 − song.acousticness` |
| Vibe bonus | up to +0.5 | Only when mood ∈ {happy, relaxed, euphoric, hopeful}: `0.5 × (0.5·valence + 0.5·danceability)` |

**Tie-breakers** (applied in order when total scores tie):

1. Higher genre points win.
2. Higher energy points win.
3. Lower `song.id` wins (keeps output deterministic for tests).

**Why these weights.** Genre and energy carry the most vibe information for this catalog and share the top weight of 2.0. Mood correlates with energy/valence, so it's kept at 1.0 to avoid double-counting. Acoustic is a small but distinct texture signal. The vibe bonus is conditional so danceability doesn't unfairly boost tracks when the user wants focus or melancholy.

### Potential biases I expect

- **Over-prioritizes genre.** With +2.0 for an exact genre match and up to +1.0 for neighbors, a great mood+energy fit in an "unrelated" genre can lose to a mediocre same-genre song. A user who loves *melancholy folk* will rarely see a *melancholy classical* track even though the vibe matches.
- **Reinforces popular genres in the catalog.** Genres with more songs (pop, lofi) have more chances to earn +2.0 matches; single-entry genres (rock, ambient, metal, reggae) can only be reached via the neighbor table. This is a **filter-bubble effect at the catalog level** — the recommender's diversity is bounded by what's in `songs.csv`.
- **Mood is under-weighted for close moods.** `focused` and `chill` are numerically nearly identical, so the mood component can't cleanly separate "background music for studying" from "music to unwind to." Real user distinctions get flattened.
- **`likes_acoustic` is binary.** A listener who wants *moderately* acoustic music (~0.6) gets the same score curve as one who wants maximum acoustic — both extremes are treated identically by the boolean flip.
- **No penalty, only reward.** Nothing subtracts points for actively-disliked features. A metalhead who "likes_acoustic = False" will still see a folk song ranked positively if the energy happens to match, because the recipe has no negative preferences.
- **Popularity/novelty blind.** The system has no notion of what's new, what the user has already heard, or what other people liked. Repeat plays and cold-start problems aren't modeled at all.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Actual terminal output from `python -m src.main` with the default `pop / happy / 0.80` profile:

```
Loaded songs: 18

User profile:
  favorite genre  : pop
  favorite mood   : happy
  target energy   : 0.80
  likes acoustic  : False

Top 5 recommendations
------------------------------------------------------------

  1. Sunrise City — Neon Echo
     Genre: pop        Mood: happy      Score: 6.19
     Why:
       - matched genre (pop) [+2.00]
       - matched mood (happy) [+1.00]
       - energy 0.82 vs target 0.80 [+1.96]
       - produced/electric texture [+0.82]
       - upbeat vibe (valence 0.84, danceability 0.79) [+0.41]

  2. Gym Hero — Max Pulse
     Genre: pop        Mood: intense    Score: 5.10
     Why:
       - matched genre (pop) [+2.00]
       - energy 0.93 vs target 0.80 [+1.74]
       - produced/electric texture [+0.95]
       - upbeat vibe (valence 0.77, danceability 0.88) [+0.41]

  3. Rooftop Lights — Indigo Parade
     Genre: indie pop  Mood: happy      Score: 4.98
     Why:
       - related genre (indie pop ~ pop) [+1.00]
       - matched mood (happy) [+1.00]
       - energy 0.76 vs target 0.80 [+1.92]
       - produced/electric texture [+0.65]
       - upbeat vibe (valence 0.81, danceability 0.82) [+0.41]

  4. Neon Sunrise Drop — Fractal Sky
     Genre: edm        Mood: euphoric   Score: 4.62
     Why:
       - related genre (edm ~ pop) [+1.00]
       - related mood (euphoric ~ happy) [+0.50]
       - energy 0.95 vs target 0.80 [+1.70]
       - produced/electric texture [+0.97]
       - upbeat vibe (valence 0.88, danceability 0.94) [+0.45]

  5. Night Drive Loop — Neon Echo
     Genre: synthwave  Mood: moody      Score: 3.98
     Why:
       - related genre (synthwave ~ pop) [+1.00]
       - energy 0.75 vs target 0.80 [+1.90]
       - produced/electric texture [+0.78]
       - upbeat vibe (valence 0.49, danceability 0.73) [+0.30]
```

The top two picks (*Sunrise City* and *Gym Hero*) are both exact `pop` genre matches, and *Sunrise City* wins because it also matches `happy` mood and sits closest to the 0.80 target energy. Every song after that earns partial credit via the genre neighbor table (`indie pop`, `edm`, `synthwave` are all in pop's family), which is exactly the "still-in-the-neighborhood" behavior the recipe was designed for.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

### Stress-testing across six personas

I defined six user profiles in [src/main.py](src/main.py) — three "sensible" personas and three adversarial edge-cases — and ran the recommender against all of them. Full terminal output below.

#### Sensible personas

**1. High-Energy Pop** — `pop / happy / 0.85 / likes_acoustic=False`

```
  1. Sunrise City — Neon Echo
     Genre: pop        Mood: happy        Score: 6.17
     Why:
       - matched genre (pop) [+2.00]
       - matched mood (happy) [+1.00]
       - energy 0.82 vs target 0.85 [+1.94]
       - produced/electric texture [+0.82]
       - upbeat vibe (valence 0.84, danceability 0.79) [+0.41]

  2. Gym Hero — Max Pulse
     Genre: pop        Mood: intense      Score: 5.20
     Why:
       - matched genre (pop) [+2.00]
       - energy 0.93 vs target 0.85 [+1.84]
       - produced/electric texture [+0.95]
       - upbeat vibe (valence 0.77, danceability 0.88) [+0.41]

  3. Rooftop Lights — Indigo Parade
     Genre: indie pop  Mood: happy        Score: 4.88
     Why:
       - related genre (indie pop ~ pop) [+1.00]
       - matched mood (happy) [+1.00]
       - energy 0.76 vs target 0.85 [+1.82]
       - produced/electric texture [+0.65]
       - upbeat vibe (valence 0.81, danceability 0.82) [+0.41]

  4. Neon Sunrise Drop — Fractal Sky
     Genre: edm        Mood: euphoric     Score: 4.72
     Why:
       - related genre (edm ~ pop) [+1.00]
       - related mood (euphoric ~ happy) [+0.50]
       - energy 0.95 vs target 0.85 [+1.80]
       - produced/electric texture [+0.97]
       - upbeat vibe (valence 0.88, danceability 0.94) [+0.45]

  5. Night Drive Loop — Neon Echo
     Genre: synthwave  Mood: moody        Score: 3.89
     Why:
       - related genre (synthwave ~ pop) [+1.00]
       - energy 0.75 vs target 0.85 [+1.80]
       - produced/electric texture [+0.78]
       - upbeat vibe (valence 0.49, danceability 0.73) [+0.30]
```

**2. Chill Lofi Study** — `lofi / focused / 0.40 / likes_acoustic=True`

```
  1. Focus Flow — LoRoom
     Genre: lofi       Mood: focused      Score: 5.78
     Why:
       - matched genre (lofi) [+2.00]
       - matched mood (focused) [+1.00]
       - energy 0.40 vs target 0.40 [+2.00]
       - acoustic-forward texture [+0.78]

  2. Library Rain — Paper Lanterns
     Genre: lofi       Mood: chill        Score: 5.26
     Why:
       - matched genre (lofi) [+2.00]
       - related mood (chill ~ focused) [+0.50]
       - energy 0.35 vs target 0.40 [+1.90]
       - acoustic-forward texture [+0.86]

  3. Midnight Coding — LoRoom
     Genre: lofi       Mood: chill        Score: 5.17
     Why:
       - matched genre (lofi) [+2.00]
       - related mood (chill ~ focused) [+0.50]
       - energy 0.42 vs target 0.40 [+1.96]
       - acoustic-forward texture [+0.71]

  4. Coffee Shop Stories — Slow Stereo
     Genre: jazz       Mood: relaxed      Score: 4.33
     Why:
       - related genre (jazz ~ lofi) [+1.00]
       - related mood (relaxed ~ focused) [+0.50]
       - energy 0.37 vs target 0.40 [+1.94]
       - acoustic-forward texture [+0.89]

  5. Spacewalk Thoughts — Orbit Bloom
     Genre: ambient    Mood: chill        Score: 4.18
     Why:
       - related genre (ambient ~ lofi) [+1.00]
       - related mood (chill ~ focused) [+0.50]
       - energy 0.28 vs target 0.40 [+1.76]
       - acoustic-forward texture [+0.92]
```

**3. Deep Intense Rock** — `rock / intense / 0.90 / likes_acoustic=False`

```
  1. Storm Runner — Voltline
     Genre: rock       Mood: intense      Score: 5.88
     Why:
       - matched genre (rock) [+2.00]
       - matched mood (intense) [+1.00]
       - energy 0.91 vs target 0.90 [+1.98]
       - produced/electric texture [+0.90]

  2. Iron Requiem — Ashen Vow
     Genre: metal      Mood: aggressive   Score: 4.32
     Why:
       - related genre (metal ~ rock) [+1.00]
       - related mood (aggressive ~ intense) [+0.50]
       - energy 0.97 vs target 0.90 [+1.86]
       - produced/electric texture [+0.96]

  3. Gym Hero — Max Pulse
     Genre: pop        Mood: intense      Score: 3.89
     Why:
       - matched mood (intense) [+1.00]
       - energy 0.93 vs target 0.90 [+1.94]
       - produced/electric texture [+0.95]

  4. Late Bloom Cypher — MC Halcyon
     Genre: hip hop    Mood: energetic    Score: 3.34
     Why:
       - related mood (energetic ~ intense) [+0.50]
       - energy 0.86 vs target 0.90 [+1.92]
       - produced/electric texture [+0.92]

  5. Night Drive Loop — Neon Echo
     Genre: synthwave  Mood: moody        Score: 2.98
     Why:
       - related mood (moody ~ intense) [+0.50]
       - energy 0.75 vs target 0.90 [+1.70]
       - produced/electric texture [+0.78]
```

#### Adversarial / edge-case personas

**4. Sad but Hyped** (conflicting mood vs. energy) — `indie pop / melancholy / 0.90 / False`

```
  1. Rooftop Lights — Indigo Parade
     Genre: indie pop  Mood: happy        Score: 4.37
     Why:
       - matched genre (indie pop) [+2.00]
       - energy 0.76 vs target 0.90 [+1.72]
       - produced/electric texture [+0.65]

  2. Night Drive Loop — Neon Echo
     Genre: synthwave  Mood: moody        Score: 3.98
     Why:
       - related genre (synthwave ~ indie pop) [+1.00]
       - related mood (moody ~ melancholy) [+0.50]
       - energy 0.75 vs target 0.90 [+1.70]
       - produced/electric texture [+0.78]

  3. Gym Hero — Max Pulse
     Genre: pop        Mood: intense      Score: 3.89
     Why:
       - related genre (pop ~ indie pop) [+1.00]
       - energy 0.93 vs target 0.90 [+1.94]
       - produced/electric texture [+0.95]

  4. Sunrise City — Neon Echo
     Genre: pop        Mood: happy        Score: 3.66
     Why:
       - related genre (pop ~ indie pop) [+1.00]
       - energy 0.82 vs target 0.90 [+1.84]
       - produced/electric texture [+0.82]

  5. Storm Runner — Voltline
     Genre: rock       Mood: intense      Score: 2.88
     Why:
       - energy 0.91 vs target 0.90 [+1.98]
       - produced/electric texture [+0.90]
```

**5. Metalhead Who Wants Acoustic** (conflicting genre vs. texture) — `metal / aggressive / 0.95 / True`

```
  1. Iron Requiem — Ashen Vow
     Genre: metal      Mood: aggressive   Score: 4.96
     Why:
       - matched genre (metal) [+2.00]
       - matched mood (aggressive) [+1.00]
       - energy 0.97 vs target 0.95 [+1.96]

  2. Storm Runner — Voltline
     Genre: rock       Mood: intense      Score: 3.52
     Why:
       - related genre (rock ~ metal) [+1.00]
       - related mood (intense ~ aggressive) [+0.50]
       - energy 0.91 vs target 0.95 [+1.92]
       - acoustic-forward texture [+0.10]

  3. Gym Hero — Max Pulse
     Genre: pop        Mood: intense      Score: 2.51
     Why:
       - related mood (intense ~ aggressive) [+0.50]
       - energy 0.93 vs target 0.95 [+1.96]
       - acoustic-forward texture [+0.05]

  4. Late Bloom Cypher — MC Halcyon
     Genre: hip hop    Mood: energetic    Score: 2.40
     Why:
       - related mood (energetic ~ aggressive) [+0.50]
       - energy 0.86 vs target 0.95 [+1.82]
       - acoustic-forward texture [+0.08]

  5. Neon Sunrise Drop — Fractal Sky
     Genre: edm        Mood: euphoric     Score: 2.00
     Why:
       - energy 0.95 vs target 0.95 [+2.00]
```

**6. Unknown Genre** (not in catalog or neighbor graph) — `k-pop / happy / 0.70 / False`

```
  1. Sunrise City — Neon Echo
     Genre: pop        Mood: happy        Score: 3.99
     Why:
       - matched mood (happy) [+1.00]
       - energy 0.82 vs target 0.70 [+1.76]
       - produced/electric texture [+0.82]
       - upbeat vibe (valence 0.84, danceability 0.79) [+0.41]

  2. Rooftop Lights — Indigo Parade
     Genre: indie pop  Mood: happy        Score: 3.94
     Why:
       - matched mood (happy) [+1.00]
       - energy 0.76 vs target 0.70 [+1.88]
       - produced/electric texture [+0.65]
       - upbeat vibe (valence 0.81, danceability 0.82) [+0.41]

  3. Harbor Sun — Coral Line
     Genre: reggae     Mood: hopeful      Score: 3.46
     Why:
       - related mood (hopeful ~ happy) [+0.50]
       - energy 0.62 vs target 0.70 [+1.84]
       - produced/electric texture [+0.72]
       - upbeat vibe (valence 0.79, danceability 0.80) [+0.40]

  4. Neon Sunrise Drop — Fractal Sky
     Genre: edm        Mood: euphoric     Score: 3.42
     Why:
       - related mood (euphoric ~ happy) [+0.50]
       - energy 0.95 vs target 0.70 [+1.50]
       - produced/electric texture [+0.97]
       - upbeat vibe (valence 0.88, danceability 0.94) [+0.45]

  5. Night Drive Loop — Neon Echo
     Genre: synthwave  Mood: moody        Score: 2.98
     Why:
       - energy 0.75 vs target 0.70 [+1.90]
       - produced/electric texture [+0.78]
       - upbeat vibe (valence 0.49, danceability 0.73) [+0.30]
```

### Accuracy check and observations

For the **Chill Lofi Study** profile, the top result is *Focus Flow* — score 5.78, hitting every single component: genre match, mood match, exact energy, acoustic-forward. This lines up perfectly with my intuition; if I imagined a "focused-study lofi" playlist, *Focus Flow* is exactly the song I'd expect at position 1. The next two picks (*Library Rain*, *Midnight Coding*) are also lofi and nearly identical numerically — that also feels right, though I noticed they're numerically almost indistinguishable, which is a real limitation the system inherits from the sparse catalog.

**Why does *Sunrise City* rank #1 for High-Energy Pop?** It's the only song in the catalog that hits **all five** scoring components at once: pop (+2.00), happy (+1.00), close to 0.85 energy (+1.94), electric texture (+0.82), and upbeat vibe (+0.41). *Gym Hero* is pop too, but its mood is `intense`, not `happy`, so it forfeits the +1.00 mood match — a 1-point gap that no amount of energy closeness makes up.

**Top-of-list repetition check** — across all six profiles, the #1 slot is filled by six *different* songs (Sunrise City, Focus Flow, Storm Runner, Rooftop Lights, Iron Requiem, Sunrise City). *Sunrise City* appears twice (as #1 for High-Energy Pop and Unknown Genre) but every other top slot is distinct. That suggests the genre weight of +2.0 is calibrated correctly — no single song is universally dominant.

**Adversarial findings** — the conflicting profiles reveal three real weaknesses:

- The *"Sad but Hyped"* profile got *Rooftop Lights* (mood: happy) at #1 despite the user asking for melancholy. Genre match (+2.0) overpowered the missing mood — the recipe can't say "genre is important *unless* the mood is completely wrong."
- The *"Metalhead + acoustic"* profile still returned metal/rock correctly, but the acoustic bonus was near-zero because those songs have `acousticness < 0.15`. The score reflects the contradiction (final scores are lower overall), but the ranking is unchanged — the user gets what they asked for on genre, and the acoustic preference is silently ignored.
- The *"k-pop"* profile falls back cleanly to whatever else scores well (pop + happy). That's actually reasonable behavior — no crash, no empty list — but the system has no way to *tell the user* "we don't have your genre."

### Weight-shift experiment: 2× energy, 0.5× genre

I temporarily changed the scoring weights in [recommender.py](src/recommender.py) — genre from `+2.0/+1.0` to `+1.0/+0.5`, energy from `up to +2.0` to `up to +4.0` — and re-ran the **High-Energy Pop** profile.

Baseline top-5:

```
  1. Sunrise City       (pop, happy)       6.17
  2. Gym Hero           (pop, intense)     5.20
  3. Rooftop Lights     (indie pop, happy) 4.88
  4. Neon Sunrise Drop  (edm, euphoric)    4.72
  5. Night Drive Loop   (synthwave, moody) 3.89
```

After (2× energy, 0.5× genre):

```
  1. Sunrise City       (pop, happy)         7.11
  2. Rooftop Lights     (indie pop, happy)   6.20
  3. Gym Hero           (pop, intense)       6.04
  4. Neon Sunrise Drop  (edm, euphoric)      6.02
  5. Late Bloom Cypher  (hip hop, energetic) 5.25
```

**What changed.** *Sunrise City* held the #1 slot — it still hits every component, so weight redistribution doesn't dethrone it. But underneath: *Rooftop Lights* jumped from #3 → #2 (its 0.76 energy is now worth ~3.64 instead of ~1.82), *Gym Hero* fell from #2 → #3 (its intense mood no longer differentiates it as much), and *Night Drive Loop* got kicked out of the top-5 entirely, replaced by *Late Bloom Cypher* (hip hop) — a genre that scored 0 for genre before, now scoring 0 for genre still but riding a nearly-perfect energy match (+3.96) into contention.

**Is the change more accurate or just different?** For this specific user ("high-energy pop"), the answer is *different, not more accurate*. Doubling energy pulls in a hip hop song at #5 that the user explicitly didn't ask for — the recipe stops respecting the "pop" declaration. But the shift did reveal something real: *Rooftop Lights* is arguably a better match for "happy pop energy" than *Gym Hero* (whose mood is `intense`), and the original weights buried it because it's only genre-adjacent (indie pop). So a small energy boost might actually help; doubling it swings too far. I reverted the weights.

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this




# Reliability Evaluation Report

**Overall:** 6 / 6 cases passed, 17 / 17 individual criteria passed.

| Case | Query | Criterion | Result | Detail |
|---|---|---|---|---|
| clear-lofi-study-request | `I want chill lofi music for studying with acoustic textures` | `top_genre_in_ambient/jazz/lofi` | ✅ Pass | top-genre='lofi', allowed=['ambient', 'jazz', 'lofi'] |
|  |  | `confidence_at_least_MEDIUM` | ✅ Pass | confidence=MEDIUM vs required≥MEDIUM |
|  |  | `no_errors_or_crashes` | ✅ Pass | error-events=0 |
|  |  | `iterations_bounded_3` | ✅ Pass | iterations=2, max=3 |
| high-energy-workout-pop | `high energy pop for my workout, upbeat and electric` | `top_genre_in_edm/indie pop/pop/synthwave` | ✅ Pass | top-genre='pop', allowed=['edm', 'indie pop', 'pop', 'synthwave'] |
|  |  | `confidence_at_least_MEDIUM` | ✅ Pass | confidence=MEDIUM vs required≥MEDIUM |
|  |  | `top_mood_matches_or_neighbors_energetic` | ✅ Pass | top-mood='intense', allowed=['aggressive', 'energetic', 'euphoric', 'intense'] |
|  |  | `no_errors_or_crashes` | ✅ Pass | error-events=0 |
| intense-rock-request | `intense rock, driving and powerful` | `top_genre_in_metal/rock` | ✅ Pass | top-genre='rock', allowed=['metal', 'rock'] |
|  |  | `no_errors_or_crashes` | ✅ Pass | error-events=0 |
| melancholy-classical-piano | `melancholy classical piano, low energy` | `top_genre_in_ambient/classical/lofi` | ✅ Pass | top-genre='classical', allowed=['ambient', 'classical', 'lofi'] |
|  |  | `no_errors_or_crashes` | ✅ Pass | error-events=0 |
| unknown-genre-graceful-fallback | `I want some k-pop hits with high energy` | `warns_on_unknown_input` | ✅ Pass | parse.warnings=['no genre matched the KB — the recommender will score on mood + energy only', "no mood matched the KB — defaulting to 'chill'"] |
|  |  | `no_errors_or_crashes` | ✅ Pass | error-events=0 |
|  |  | `iterations_bounded_3` | ✅ Pass | iterations=2, max=3 |
| empty-query-does-not-crash | `` | `no_errors_or_crashes` | ✅ Pass | error-events=0 |
|  |  | `iterations_bounded_3` | ✅ Pass | iterations=3, max=3 |

## Per-case agent trace summary

### clear-lofi-study-request

```
Query: 'I want chill lofi music for studying with acoustic textures'
Parsed profile: {'genre': 'lofi', 'mood': 'focused', 'extra_mood_tags': 'studying|focused|calm', 'energy': 0.4, 'likes_acoustic': True}
Ran 2 iteration(s), mode=balanced, diversity=True
Aggregate confidence: 0.54 (MEDIUM)

-----------------------------------------------------------------------
#  Title                 Artist          Genre      Mood          Score
-----------------------------------------------------------------------
1  Focus Flow            LoRoom          lofi       focused        6.28
     · matched genre (lofi) [+2.00]
     · matched mood (focused) [+1.00]
     · energy 0.40 vs target 0.40 [+2.00]
     · acoustic-forward texture [+0.78]
     · mood tags ['calm', 'studying'] [+0.50]

2  Library Rain          Paper Lanterns  lofi       chill          5.26
     · matched genre (lofi) [+2.00]
     · related mood (chill ~ focused) [+0.50]
     · energy 0.35 vs target 0.40 [+1.90]
     · acoustic-forward texture [+0.86]

3  Coffee Shop Stories   Slow Stereo     jazz       relaxed        4.33
     · related genre (jazz ~ lofi) [+1.00]
     · related mood (relaxed ~ focused) [+0.50]
     · energy 0.37 vs target 0.40 [+1.94]
     · acoustic-forward texture [+0.89]

4  Spacewalk Thoughts    Orbit Bloom     ambient    chill          4.18
     · related genre (ambient ~ lofi) [+1.00]
     · related mood (chill ~ focused) [+0.50]
     · energy 0.28 vs target 0.40 [+1.76]
     · acoustic-forward texture [+0.92]

5  Winter Prelude        Aria Sonn       classical  melancholy     3.59
     · related genre (classical ~ lofi) [+1.00]
     · energy 0.22 vs target 0.40 [+1.64]
     · acoustic-forward texture [+0.95]

-----------------------------------------------------------------------
```

### high-energy-workout-pop

```
Query: 'high energy pop for my workout, upbeat and electric'
Parsed profile: {'genre': 'pop', 'mood': 'energetic', 'extra_mood_tags': 'pumping|motivational', 'energy': 0.9, 'likes_acoustic': False}
Ran 2 iteration(s), mode=balanced, diversity=True
Aggregate confidence: 0.51 (MEDIUM)

-----------------------------------------------------------------------
#  Title                 Artist          Genre      Mood          Score
-----------------------------------------------------------------------
1  Gym Hero              Max Pulse       pop        intense        5.89
     · matched genre (pop) [+2.00]
     · related mood (intense ~ energetic) [+0.50]
     · energy 0.93 vs target 0.90 [+1.94]
     · produced/electric texture [+0.95]
     · mood tags ['motivational', 'pumping'] [+0.50]

2  Sunrise City          Neon Echo       pop        happy          4.66
     · matched genre (pop) [+2.00]
     · energy 0.82 vs target 0.90 [+1.84]
     · produced/electric texture [+0.82]

3  Neon Sunrise Drop     Fractal Sky     edm        euphoric       4.37
     · related genre (edm ~ pop) [+1.00]
     · related mood (euphoric ~ energetic) [+0.50]
     · energy 0.95 vs target 0.90 [+1.90]
     · produced/electric texture [+0.97]

4  Late Bloom Cypher     MC Halcyon      hip hop    energetic      3.84
     · matched mood (energetic) [+1.00]
     · energy 0.86 vs target 0.90 [+1.92]
     · produced/electric texture [+0.92]

5  Storm Runner          Voltline        rock       intense        3.38
     · related mood (intense ~ energetic) [+0.50]
     · energy 0.91 vs target 0.90 [+1.98]
     · produced/electric texture [+0.90]

-----------------------------------------------------------------------
```

### intense-rock-request

```
Query: 'intense rock, driving and powerful'
Parsed profile: {'genre': 'rock', 'mood': 'intense', 'extra_mood_tags': 'driving|adrenaline', 'energy': 0.9, 'likes_acoustic': False}
Ran 1 iteration(s), mode=balanced, diversity=False
Aggregate confidence: 0.48 (LOW)

-----------------------------------------------------------------------
#  Title                 Artist          Genre      Mood          Score
-----------------------------------------------------------------------
1  Storm Runner          Voltline        rock       intense        6.38
     · matched genre (rock) [+2.00]
     · matched mood (intense) [+1.00]
     · energy 0.91 vs target 0.90 [+1.98]
     · produced/electric texture [+0.90]
     · mood tags ['adrenaline', 'driving'] [+0.50]

2  Iron Requiem          Ashen Vow       metal      aggressive     4.32
     · related genre (metal ~ rock) [+1.00]
     · related mood (aggressive ~ intense) [+0.50]
     · energy 0.97 vs target 0.90 [+1.86]
     · produced/electric texture [+0.96]

3  Gym Hero              Max Pulse       pop        intense        3.89
     · matched mood (intense) [+1.00]
     · energy 0.93 vs target 0.90 [+1.94]
     · produced/electric texture [+0.95]

4  Late Bloom Cypher     MC Halcyon      hip hop    energetic      3.34
     · related mood (energetic ~ intense) [+0.50]
     · energy 0.86 vs target 0.90 [+1.92]
     · produced/electric texture [+0.92]

5  Night Drive Loop      Neon Echo       synthwave  moody          2.98
     · related mood (moody ~ intense) [+0.50]
     · energy 0.75 vs target 0.90 [+1.70]
     · produced/electric texture [+0.78]

-----------------------------------------------------------------------
```

### melancholy-classical-piano

```
Query: 'melancholy classical piano, low energy'
Parsed profile: {'genre': 'classical', 'mood': 'melancholy', 'energy': 0.2, 'likes_acoustic': True}
Ran 2 iteration(s), mode=balanced, diversity=True
Aggregate confidence: 0.45 (LOW)

-----------------------------------------------------------------------
#  Title                 Artist          Genre      Mood          Score
-----------------------------------------------------------------------
1  Winter Prelude        Aria Sonn       classical  melancholy     5.91
     · matched genre (classical) [+2.00]
     · matched mood (melancholy) [+1.00]
     · energy 0.22 vs target 0.20 [+1.96]
     · acoustic-forward texture [+0.95]

2  Spacewalk Thoughts    Orbit Bloom     ambient    chill          3.76
     · related genre (ambient ~ classical) [+1.00]
     · energy 0.28 vs target 0.20 [+1.84]
     · acoustic-forward texture [+0.92]

3  Library Rain          Paper Lanterns  lofi       chill          3.56
     · related genre (lofi ~ classical) [+1.00]
     · energy 0.35 vs target 0.20 [+1.70]
     · acoustic-forward texture [+0.86]

4  Focus Flow            LoRoom          lofi       focused        3.38
     · related genre (lofi ~ classical) [+1.00]
     · energy 0.40 vs target 0.20 [+1.60]
     · acoustic-forward texture [+0.78]

5  Old Barn Radio        Willow & Wren   folk       nostalgic      3.10
     · related mood (nostalgic ~ melancholy) [+0.50]
     · energy 0.34 vs target 0.20 [+1.72]
     · acoustic-forward texture [+0.88]

-----------------------------------------------------------------------
```

### unknown-genre-graceful-fallback

```
Query: 'I want some k-pop hits with high energy'
Parsed profile: {'energy': 0.9, 'genre': '__unknown__', 'mood': 'chill', 'likes_acoustic': False}
  WARN: no genre matched the KB — the recommender will score on mood + energy only
  WARN: no mood matched the KB — defaulting to 'chill'
Ran 2 iteration(s), mode=mood-first, diversity=False
Aggregate confidence: 0.41 (LOW)
Critic findings:
  [WARN] PARSE_WARNING: no genre matched the KB — the recommender will score on mood + energy only
  [WARN] PARSE_WARNING: no mood matched the KB — defaulting to 'chill'

-----------------------------------------------------------------------
#  Title                 Artist          Genre      Mood          Score
-----------------------------------------------------------------------
1  Midnight Coding       LoRoom          lofi       chill          4.33
     · matched mood (chill) [+3.00]
     · energy 0.42 vs target 0.90 [+1.04]
     · produced/electric texture [+0.29]

2  Library Rain          Paper Lanterns  lofi       chill          4.04
     · matched mood (chill) [+3.00]
     · energy 0.35 vs target 0.90 [+0.90]
     · produced/electric texture [+0.14]

3  Spacewalk Thoughts    Orbit Bloom     ambient    chill          3.84
     · matched mood (chill) [+3.00]
     · energy 0.28 vs target 0.90 [+0.76]
     · produced/electric texture [+0.08]

4  Gym Hero              Max Pulse       pop        intense        2.89
     · energy 0.93 vs target 0.90 [+1.94]
     · produced/electric texture [+0.95]

5  Storm Runner          Voltline        rock       intense        2.88
     · energy 0.91 vs target 0.90 [+1.98]
     · produced/electric texture [+0.90]

-----------------------------------------------------------------------
```

### empty-query-does-not-crash

```
Query: ''
Parsed profile: {'genre': 'pop', 'mood': 'chill', 'energy': 0.5, 'likes_acoustic': False}
  WARN: empty query — falling back to a neutral profile
Ran 3 iteration(s), mode=mood-first, diversity=True
Aggregate confidence: 0.48 (LOW)
Critic findings:
  [WARN] PARSE_WARNING: empty query — falling back to a neutral profile

-----------------------------------------------------------------------
#  Title                 Artist          Genre      Mood          Score
-----------------------------------------------------------------------
1  Midnight Coding       LoRoom          lofi       chill          5.13
     · matched mood (chill) [+3.00]
     · energy 0.42 vs target 0.50 [+1.84]
     · produced/electric texture [+0.29]

2  Library Rain          Paper Lanterns  lofi       chill          4.84
     · matched mood (chill) [+3.00]
     · energy 0.35 vs target 0.50 [+1.70]
     · produced/electric texture [+0.14]

3  Spacewalk Thoughts    Orbit Bloom     ambient    chill          4.64
     · matched mood (chill) [+3.00]
     · energy 0.28 vs target 0.50 [+1.56]
     · produced/electric texture [+0.08]

4  Coffee Shop Stories   Slow Stereo     jazz       relaxed        3.35
     · related mood (relaxed ~ chill) [+1.50]
     · energy 0.37 vs target 0.50 [+1.74]
     · produced/electric texture [+0.11]

5  Sunrise City          Neon Echo       pop        happy          3.18
     · matched genre (pop) [+1.00]
     · energy 0.82 vs target 0.50 [+1.36]
     · produced/electric texture [+0.82]

-----------------------------------------------------------------------
```

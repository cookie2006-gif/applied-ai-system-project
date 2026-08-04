# Model Card — VibeMatch 2.0

## 1. Model name and version

**VibeMatch 2.0** — an agent-driven, deterministic content-based music
recommender with structured self-critique and a reliability harness.
Built on top of the base project *VibeMatch 1.0* (a one-shot points-based
scorer over 18 songs), which is documented in the base project's model
card content preserved in Section 10 below.

---

## 2. Intended use

VibeMatch 2.0 is a **classroom / portfolio system** demonstrating an
end-to-end applied AI pipeline: NL → retrieval → structured scoring →
self-critique → refinement → confidence-labeled output.

**Who it's for.** A student, reviewer, or interviewer who wants to
inspect an agentic workflow end-to-end. Every stage of the pipeline is
readable in under 250 lines of Python and every decision is traceable
through the structured log.

**What this is NOT for.** Serving real listeners, ranking real
artists, or making any decision that affects a real user's experience.
The catalog is 18 hand-authored rows. The scoring weights and the KB
triggers are both hand-tuned, not learned. Confidence scores are
comparisons against a theoretical maximum, not calibrated against real
human ratings.

---

## 3. How the model works (at a glance)

1. **Planner** parses the NL query against a small music-domain KB
   (`src/kb/music_terms.md`), producing a structured profile and a
   list of parse warnings. Unknown-genre / unknown-mood queries are
   flagged, not guessed.
2. **Recommender** (the base project's original engine) scores every
   song against the profile using additive component points and one
   of four scoring modes.
3. **Critic** normalizes scores to per-song confidences in [0, 1],
   averages them for an aggregate label (`HIGH` ≥ 0.75, `MEDIUM` ≥ 0.5,
   `LOW` otherwise, capped at MEDIUM if any parse warning fired), and
   emits typed findings for known failure modes.
4. **Refiner** picks the highest-severity actionable finding and
   translates it into a strategy change (mode swap or diversity
   toggle), then loops. Bounded to 3 iterations.
5. **Reliability harness** re-runs the whole pipeline against 6
   curated cases with typed pass/fail criteria on every commit.

Details in the [README architecture section](README.md#architecture).

---

## 4. Data

- **Catalog.** `data/songs.csv`, 18 songs × 15 columns (10 base
  features + 5 added in the base project: popularity, decade,
  mood_tags, instrumental, language). Every value hand-authored — no
  actual audio-feature measurements.
- **Knowledge base.** `src/kb/music_terms.md`, 6 field groups
  (genre, mood, energy, extra_mood_tags, likes_acoustic,
  prefers_instrumental, popularity_preference) with a total of ~80
  trigger keywords across 47 canonical values. Editable without
  touching code — a domain curator can add a new genre by editing the
  Markdown, not the parser.
- **Test cases.** 6 curated NL queries in `src/evaluation.py` with
  typed criteria. Chosen to cover the four common categories: clean
  intent, mixed-signal intent, unknown input, and pathological input
  (empty string, garbage tokens).
- **What's missing.** No listening history, no user feedback loop, no
  demographic data, no external audio embeddings, no time-of-day
  context. Nothing about the user is stored between runs.

---

## 5. AI collaboration on this project

This project was built in Claude Code (Claude Opus 4.7 via the VS Code
extension), continuing the collaboration begun on VibeMatch 1.0. The
transcript of the base project's per-challenge collaboration is
preserved in [`ai_interactions.md`](ai_interactions.md). What follows
is a reflection on the new work in VibeMatch 2.0.

### One AI suggestion that was genuinely helpful

When I described the goal — "wrap the scorer in something that can
read natural language and self-correct" — my first instinct was to
add an LLM API call at the front (parse the query with GPT/Claude,
call the scorer, done). The assistant pushed back and asked whether
the parser and the critic needed to be an LLM at all, given (a) the
domain vocabulary is tiny and mostly closed (15 genres, 14 moods,
etc.), and (b) making the parser deterministic would let me write
regression tests that mean something. That framing landed. A trigger
table over a KB file is enough for this vocabulary size, and it means
`test_reliability_harness_all_cases_pass` is a real assertion rather
than a probabilistic one. If I'd gone with the LLM-first route the
"agentic workflow" would have been a thin wrapper around a black box;
what I have instead is a system whose behavior I can inspect at every
step.

### One AI suggestion that was flawed (and how I caught it)

The critic module was initially generated with a `LOW_TOP_SCORE`
finding that fired whenever the #1 pick's raw score fell below 4.0.
When I ran it against the melancholy-classical query, the finding
fired even though *Winter Prelude* (5.91) was clearly the right #1.
The bug was subtle: the threshold was hardcoded in absolute-score
units, but the *average* raw score varies wildly by profile
(high-energy pop queries typically score higher than any single-genre
requests because pop has more catalog entries to stack points from).
An absolute threshold conflated "the top pick is bad" with "this
profile can't score high in this catalog." I replaced it with the
`LOW_AGGREGATE_CONFIDENCE` finding that operates on the *normalized*
[0, 1] confidence, and moved the ceiling logic into the label
assignment. Lesson: any time an AI-generated check uses a magic
number, I should ask whether that number is scale-invariant or
scale-dependent — this one wasn't.

### How I collaborated across the whole project

The pattern I noticed in VibeMatch 1.0 held in 2.0: the assistant was
fastest and most useful on **scaffolding** (dataclasses, JSON log
format, ASCII table renderer, README structure) and slowest on
**runtime judgment** (which threshold, which weight, which fallback
mode makes sense for THIS catalog). When I trusted the assistant on
scaffolding and re-ran the harness after every substantive change, I
made steady progress. When I trusted it on runtime judgment without
running the code, I found bugs later. The takeaway I'll carry into
future projects: treat the assistant as a fast co-author for
structure and a bad estimator for numerics. Run the code every time
the numbers change.

---

## 6. Limitations and biases

**Inherited from VibeMatch 1.0:**

- **Catalog filter bubble.** 18 songs across 15 genres means every
  single-entry genre (rock, ambient, jazz, metal, reggae, r&b, hip
  hop, folk, country, classical, edm) can only be recommended to a
  user whose profile matches it exactly or falls into its neighbor
  family. Pop and lofi are structurally advantaged.
- **No negative preferences.** The recipe rewards preferences and
  cannot penalize actively-disliked features. A metalhead who also
  likes acoustic music still gets metal ranked first.
- **Numerically-close moods are indistinguishable.** `chill`,
  `focused`, and `relaxed` all map to similar energy/valence ranges,
  so the mood component can't cleanly separate "study" from
  "unwind."

**Introduced by the 2.0 agent layer:**

- **Parser is brittle outside the KB.** Because I chose determinism
  over LLM generalization, any query using vocabulary not in
  `src/kb/music_terms.md` degrades to LOW confidence with a parse
  warning. This is honest (the system tells the user it's guessing)
  but also limits the range of phrasings the system handles well
  without KB updates.
- **Confidence is normalized against a theoretical max, not
  calibrated.** Aggregate confidence of 0.54 means "the top-5 stacked
  up 54% of the maximum possible points against this profile." It
  does **not** mean "there's a 54% chance the user will like the top
  pick." Reading the label as a real-world probability would be
  wrong.
- **Critic checks are a fixed list.** The critic catches artist
  repetition, mood-mismatch, low aggregate confidence, flat score
  curves, empty results, and parse warnings. It does not catch
  novel failure modes (e.g. a subtle bias I haven't thought of).
  Every new class of failure I want to detect needs a new critic
  check.
- **Confidence-cap logic depends on presence of PARSE_WARNING codes,
  not their meaning.** A benign parse warning (e.g. no energy cue
  detected → defaulting to 0.5) caps confidence at MEDIUM the same
  way a critical one (unknown genre) does. This is conservative-safe
  but occasionally under-labels a genuinely-good result.

**Bias I actively looked for and could not fully eliminate:**

- **Popularity feedback loop across the KB and the catalog.** The KB
  has more mood triggers for `happy` and `energetic` than for
  `nostalgic` or `wistful`, because I wrote it and I default to
  upbeat vocabulary when brainstorming. A user who describes their
  mood in a less common register gets fewer parse hits, which
  triggers a PARSE_WARNING, which caps their confidence at MEDIUM.
  The system may under-serve users whose vocabulary doesn't match
  mine — even when the catalog *could* serve them well. I documented
  this here but did not fix it; the fix is either "expand the KB with
  a diverse curator" or "add an LLM fallback for parse misses,"
  neither of which is in scope for the current project.

---

## 7. Evaluation

The reliability harness ([`src/evaluation.py`](src/evaluation.py))
runs 6 curated NL queries through the full pipeline and evaluates each
against typed criteria. Latest results (also in
[`evaluation_report.md`](evaluation_report.md) and
[`evaluation_report.json`](evaluation_report.json)):

**Summary — 6/6 cases passed, 17/17 individual criteria passed.**

| Case | Query | Iterations | Mode | Diversity | Confidence | Result |
|---|---|---|---|---|---|---|
| clear-lofi-study-request | *"chill lofi music for studying with acoustic textures"* | 2 | balanced | on | MEDIUM | ✅ 4/4 |
| high-energy-workout-pop | *"high energy pop for my workout, upbeat and electric"* | 2 | balanced | on | MEDIUM | ✅ 4/4 |
| intense-rock-request | *"intense rock, driving and powerful"* | 1 | balanced | off | MEDIUM | ✅ 2/2 |
| melancholy-classical-piano | *"melancholy classical piano, low energy"* | 2 | balanced | on | LOW | ✅ 2/2 |
| unknown-genre-graceful-fallback | *"I want some k-pop hits with high energy"* | 2 | mood-first | off | LOW | ✅ 3/3 |
| empty-query-does-not-crash | *(empty string)* | 3 | mood-first | on | LOW | ✅ 2/2 |

**What passed and why.**

- Every case terminated within the 3-iteration budget.
- No case crashed or emitted an error-level log record.
- Every clean query landed the correct genre or a KB-declared
  neighbor at #1.
- The unknown-genre case correctly emitted the "no genre matched"
  warning instead of silently picking a plausible substitute.
- Confidence labels degraded honestly — the melancholy-classical and
  unknown-genre cases both landed LOW, which is what I want (there is
  genuinely only one classical song in this catalog).

**What surprised me.**

- The high-energy workout query switched to `diversity=True` in
  iteration 2 because *Neon Echo* had two songs in the initial top-5.
  I hadn't predicted that specific catalog fact — the harness caught
  it and the log made it visible.
- The empty-query case took the full 3 iterations because the
  neutral-fallback profile triggered a chain of unrelated critiques
  (mood mismatch → mode swap → artist repetition → diversity toggle).
  This is the loop working as designed but it's also the closest the
  system comes to "wasted work" — three iterations to land on a LOW
  result. If real users routinely submitted empty queries, the right
  fix is a `GUARD` in the planner that short-circuits early.

**What I'd add next.**

- A **latency budget** criterion (the agent must return in under N ms
  even on pathological input).
- A **differential test** that compares two adjacent catalog versions
  and reports which top-K positions shifted, so I can spot instability
  from small data edits.
- **Calibrated confidence** — collect real human ratings for the six
  demo queries and fit a mapping from normalized score → predicted
  human like/dislike probability. This is the biggest single lever
  for making the confidence label mean what a user would assume.

---

## 8. Future work

The three top priorities carried forward from VibeMatch 1.0 remain:

1. **Negative preferences** on the profile.
2. **Continuous `target_acousticness`** instead of a boolean.
3. **A context field** on the profile (`studying` vs. `commuting`
   etc.).

New priorities added in VibeMatch 2.0:

4. **Add an LLM fallback for parse failures.** Keep the deterministic
   KB parser as the primary path (for testability), but when it hits
   `__unknown__` or emits multiple warnings, escalate to an LLM to
   normalize the query. This buys generalization without giving up
   the deterministic core.
5. **Calibrated confidence via real ratings.** See Section 7.
6. **A latency budget and a differential harness.** See Section 7.
7. **Grow the catalog to 3+ songs per genre.** This is the single
   biggest lever for lifting confidence off the LOW/MEDIUM floor.

---

## 9. Responsible-AI reflection (project-wide)

Building the 2.0 agent layer on top of 1.0's scorer taught me the
distinction between "AI-enabled" and "AI-shaped." The base scorer was
strictly rules; adding the plan/critique/refine loop makes the *shape*
of the system agentic without changing the fact that the actual
decisions are deterministic and inspectable. This distinction matters
for portfolio-grade work: I can hand this repo to a reviewer and every
line of behavior can be traced, unlike a system where "the LLM
decided" is the entire explanation. That's the kind of applied AI I
want to be building — auditable end-to-end, with the AI-ness
concentrated in shape (plan, act, critique, refine, self-correct)
rather than in an opaque prediction call.

The harder question — the one this project surfaces but doesn't
resolve — is what happens when the deterministic core is
under-specified for a real user population. The KB in Section 6
under-serves users whose mood vocabulary differs from mine. In a
production system I'd need either a diverse KB curator group or an
LLM fallback, and both introduce new failure modes I haven't tested
for. Recognizing that is more valuable to me right now than pretending
I've solved it.

---

## 10. Preserved content — VibeMatch 1.0 model card sections

The base project's model card sections (intended use, how it works,
data, strengths, and the earlier evaluation across six structured
personas) are preserved below for continuity. The 2.0 material above
supersedes them where they overlap.

### 1.0 · Intended use

VibeMatch 1.0 takes a small "taste profile" (favorite genre, favorite
mood, target energy 0–1, likes-acoustic flag) and returns five songs
from an 18-song catalog with a plain-English reason for each pick.
Designed as a classroom exercise — a tiny, readable recommender you
can trace end-to-end.

### 1.0 · How the model works

Each song has a genre, mood, and audio features (energy, valence,
danceability, acousticness) between 0 and 1. Points are awarded for
each matching component; ties broken by genre → energy → id.
Full recipe in the README.

### 1.0 · Data

Same 18-song CSV as 2.0. Hand-authored, no real audio features.

### 1.0 · Strengths

- Handles extreme profiles cleanly.
- Every recommendation comes with a plain reason.
- Deterministic and testable.
- Neighbor tables prevent brittle cliffs.
- Small enough to read end-to-end.

### 1.0 · Six-persona evaluation

*See the README's "Sample interactions" and the base project's
`ai_interactions.md` for the full six-persona output and the
weight-shift experiment.*

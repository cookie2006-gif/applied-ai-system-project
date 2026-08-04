# VibeMatch 2.0 — an Applied AI Music Recommender

**Base project (Module 1–3):** [Music Recommender Simulation](#).
The starter project was a small rules-based content-based recommender
that scored 18 hand-authored songs against a structured `UserProfile`
(favorite genre, favorite mood, target energy, likes-acoustic flag) and
returned the top-K with a per-song reason. It ran end-to-end but was
strictly a "one-shot, structured-in, structured-out" scoring engine —
no natural-language input, no self-correction, no reliability testing.

**What this project does.** VibeMatch 2.0 wraps that scoring engine in
an **agentic workflow** that turns a natural-language request into a
ranked list of songs with a confidence label. The agent plans (parses
the query against a small music-domain knowledge base), acts (calls
the scoring engine), critiques (inspects the top-K for scoring
failures, low confidence, or artist repetition), and refines (switches
scoring mode or enables the diversity re-ranker) up to three
iterations before returning. A structured reliability harness of six
adversarial test cases verifies the whole pipeline on every commit.

---

## Why this matters

A rules-based recommender can be dead-accurate on *structured* input
and still be useless in a real product, because real users don't hand
you a JSON. They type "I want chill lofi for studying" and expect an
answer. Wrapping the scoring core in a plan/act/critique/refine loop
does three things a one-shot scorer can't:

1. **Meets users where they are** — the NL front-end accepts free-form
   text and turns it into a structured profile via retrieval from a
   small knowledge base.
2. **Reports its own confidence** — instead of always returning a
   top-5 as if it were perfect, every response is labeled `HIGH`,
   `MEDIUM`, or `LOW` based on how well the catalog actually fit the
   request.
3. **Self-corrects** — when the critic flags a specific problem (top
   pick's mood doesn't match, top-K is dominated by one artist, etc.)
   the agent picks a different scoring strategy and re-runs.

---

## Architecture

The system is a pipeline of four stages, wired together in
[src/agent.py](src/agent.py). Every stage is a plain Python module with
no external LLM calls — the agent is deterministic and offline.

![Architecture](diagrams/architecture.mmd)

> The diagram lives in
> [`diagrams/architecture.mmd`](diagrams/architecture.mmd). Paste its
> contents into <https://mermaid.live> to view it, or open it in a
> Markdown viewer that supports Mermaid (GitHub, VS Code).

**Data flow.**

```
NL query ─► planner ─► profile + strategy ─► recommender ─► top-K
                                                              │
                                                              ▼
                                                            critic
                                                              │
                                                         findings + confidence
                                                              │
              ┌──────────────────── refiner ◄─────────────────┘
              │  (if actionable)
              ▼
         new mode / diversity ──► loop back to recommender  (max 3 iterations)
              │
              └────────────► (nothing left to fix) ──► AgentResult ─► user
```

**Component responsibilities.**

| Stage | File | What it does |
|---|---|---|
| Planner | [src/query_parser.py](src/query_parser.py) + [src/kb/music_terms.md](src/kb/music_terms.md) | Parses the NL query by retrieving matched chunks from a small music-domain KB, producing a structured `UserProfile` dict plus a list of parse warnings. |
| Recommender (act) | [src/recommender.py](src/recommender.py) | The original additive-scoring engine, unchanged. Reads `data/songs.csv`, scores every song against the profile using one of four `SCORING_MODES`, applies the diversity re-ranker if requested, returns top-K with reasons. |
| Critic | [src/critic.py](src/critic.py) | Reviews the top-K and emits typed findings (`TOP_MOOD_MISMATCH`, `ARTIST_REPETITION`, `LOW_AGGREGATE_CONFIDENCE`, `FLAT_SCORE_CURVE`, `EMPTY_RESULTS`, `PARSE_WARNING`). Computes per-song and aggregate confidence in [0, 1] and labels it HIGH/MEDIUM/LOW. |
| Refiner | [src/agent.py](src/agent.py) `_refine` | Picks the highest-severity actionable finding, translates it into a strategy change (mode swap or diversity toggle), and loops. Loop is bounded (`MAX_ITERATIONS = 3`) and each remediation can fire at most once per run. |
| Reliability harness | [src/evaluation.py](src/evaluation.py) | 6 curated test cases × typed criteria → `evaluation_report.md` / `.json`. Also wired into `pytest` as a single end-to-end regression check. |
| Logging | [src/logger.py](src/logger.py) | Every stage emits a structured JSON event to a per-run `RunLog`; the full trace is flushed to `logs/agent_run.jsonl` on `main.py` runs. |

---

## Setup

```bash
# 1. Clone
git clone <this-repo-url> vibematch
cd vibematch

# 2. Create a virtualenv (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate     # macOS / Linux
# .venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the demo (6 built-in NL queries)
python3 -m src.main

# 5. Run the reliability harness (writes evaluation_report.md/.json)
python3 -m src.evaluation

# 6. Run the tests
python3 -m pytest -q
```

**Reproducibility.** The whole system is deterministic. Every run of
`python3 -m src.main` against a fixed catalog produces the same
recommendations, the same confidence values, and the same log trace.
Reference outputs live in:

- [`assets/sample_run.txt`](assets/sample_run.txt) — full stdout from
  the six-query demo, including formatted recommendations tables.
- [`assets/sample_run_trace.txt`](assets/sample_run_trace.txt) — the
  agent's plan/act/critique/refine trace for every query.
- [`evaluation_report.md`](evaluation_report.md) — the pass/fail table
  from the reliability harness.

---

## Sample interactions

Three inputs, three outputs — all copied verbatim from
[`assets/sample_run.txt`](assets/sample_run.txt). No screenshots, no
video required.

### Example 1 — clean-fit query, critic asks for diversity

```
[1/6] clear lofi study request
==============================================================================
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
```

**What happened in the loop.** Iteration 1 returned *Focus Flow* and
*Midnight Coding* — both by LoRoom — at #1 and #2. The critic emitted
`ARTIST_REPETITION`. Iteration 2 re-ran with `diversity=True`; *Focus
Flow* held #1, but the second LoRoom song was demoted and *Library
Rain* was promoted. No more findings, agent stops.

### Example 2 — the agent switches scoring mode mid-run

```
[2/6] high-energy workout
==============================================================================
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
```

**What happened in the loop.** The parser extracted `mood=energetic`
from "upbeat", but *Gym Hero* is tagged `intense` — a neighbor mood.
The critic didn't flag it (intense is in the neighbor set of
energetic), so no mode swap. Iteration 2 was triggered by
`ARTIST_REPETITION` alone (two Neon Echo songs originally at #2 and
#5). Diversity was enabled; the second Neon Echo song was demoted;
*Neon Sunrise Drop* took its spot. This is the exact happy path the
critic-refiner loop was designed for.

### Example 3 — unknown input, graceful fallback + honest LOW confidence

```
[4/6] unknown-genre fallback
==============================================================================
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
```

**What happened.** "k-pop" isn't in the KB and "high energy" isn't a
mood word — the parser correctly emits two warnings and populates a
sentinel `__unknown__` genre. The recommender degrades gracefully to
mood + energy scoring. Because two parse warnings fired, the
confidence label is capped at `LOW` regardless of the raw score — the
system tells the user "I'm not sure about this one" instead of
pretending everything is fine. This is the guardrail-driven behavior
the harness's `warns_on_unknown_input` criterion enforces.

---

## Design decisions

### Why an agent, not just a scorer?

The base project's scorer already worked. Wrapping it in an agent
buys three specific behaviors that a one-shot scorer can't offer:

1. **NL input without an LLM** — the KB + trigger-match retriever
   handles typical queries deterministically. When a query falls
   outside the KB, the system fails loud (warnings + LOW confidence)
   rather than silently guessing.
2. **Confidence honesty** — normalizing raw scores against the
   theoretical maximum lets the system report `HIGH`/`MEDIUM`/`LOW`.
   A user can now tell "this catalog is a good fit" from "this is the
   best I can do, but it's a stretch."
3. **Self-correction on real failure modes** — artist stacking
   (LoRoom × 3) and mood misfits are the two most common critiques a
   human would offer, so the critic checks for exactly those.

### Deterministic vs. LLM-driven

I deliberately built the agent as a *deterministic pipeline* rather
than as an LLM wrapper. Two reasons:

- **Portfolio reproducibility.** Anyone cloning this repo can run the
  exact same demo, the exact same harness, and get identical output.
  No API keys, no rate limits, no version drift.
- **Testable control flow.** Because the agent's decisions are
  driven by structured findings from the critic (not by free-form
  LLM output), I can write pytest assertions like "the agent must
  react within 3 iterations" or "the agent must flag unknown
  genres" and have them mean something.

The trade-off is that the NL parser is brittle to phrasings outside
the KB — an LLM would generalize better. In a real system I'd add an
LLM fallback for parse failures. Here, I chose to surface those
failures explicitly instead of hiding them.

### Why a KB-file for retrieval, not a hardcoded dict

The parser reads `src/kb/music_terms.md` at import time. Adding a new
genre or mood trigger means editing the Markdown file, not the
Python. The `- value  triggers: keywords` format is designed to be
edited by a domain expert without touching code. This mirrors the
"data over dispatch" pattern the base project used for
`SCORING_MODES`.

### Trade-offs I accepted

- **Small catalog cap on confidence.** 18 songs across 15 genres means
  most single-genre requests can only fill 1–2 slots with an exact
  match. Aggregate confidence is honest, but often lands MEDIUM/LOW
  for that reason. Growing the catalog is the biggest single lever
  for better numbers.
- **Critic reacts to codes, not messages.** Findings have short codes
  (`TOP_MOOD_MISMATCH`) so the refiner branches on them. This means
  adding a new finding type requires wiring both the critic and the
  refiner.
- **Loop bound of 3.** Empirically nothing productive happens after
  three refine passes on this catalog — the agent runs out of new
  strategies to try. This is a hardcoded ceiling on wasted work.

---

## Testing summary

**Automated tests.** `pytest -q` currently runs **15 tests in 0.03s**,
all passing:

- 2 legacy tests carried forward from the base project (sanity check
  the underlying scorer against the `Song`/`UserProfile` dataclasses).
- 13 new tests in [`tests/test_agent.py`](tests/test_agent.py)
  covering the query parser, critic, agent loop, and a full
  end-to-end run of the reliability harness.

**Reliability harness.** [`src/evaluation.py`](src/evaluation.py) runs
6 curated cases through the agent and checks each against typed
criteria. Latest results (in
[`evaluation_report.md`](evaluation_report.md)):

| # | Case | Query | Pass? |
|---|---|---|---|
| 1 | clear-lofi-study-request | *"I want chill lofi music for studying with acoustic textures"* | ✅ 4/4 criteria |
| 2 | high-energy-workout-pop | *"high energy pop for my workout, upbeat and electric"* | ✅ 4/4 criteria |
| 3 | intense-rock-request | *"intense rock, driving and powerful"* | ✅ 2/2 criteria |
| 4 | melancholy-classical-piano | *"melancholy classical piano, low energy"* | ✅ 2/2 criteria |
| 5 | unknown-genre-graceful-fallback | *"I want some k-pop hits with high energy"* | ✅ 3/3 criteria |
| 6 | empty-query-does-not-crash | (empty string) | ✅ 2/2 criteria |

**Overall: 6/6 cases passed, 17/17 criteria passed.**

**What was hard.** The parser initially matched "pop" inside "k-pop"
because I used naive substring matching, which meant the unknown-genre
test spuriously passed with a wrong-but-plausible fallback. The
tokenizer now splits on whitespace and only matches whole tokens for
single-word triggers — the harness caught this regression the moment I
added it. That's exactly the point of the harness.

**What the numbers tell me.** Aggregate confidence for the six demo
queries lands MEDIUM (three cases) or LOW (three cases). The LOW ones
are honest — they correspond to sparse-genre requests (classical) or
underspecified queries (empty, k-pop). The MEDIUM ones are also
honest — the catalog has 2–4 direct matches for those queries but
positions 3–5 have to reach into neighbor genres. If the aggregate
were HIGH for every case, I'd distrust it.

**What I'd add next.** A latency budget test (the agent should always
return within N ms even on a pathological query), and a differential
test that compares two adjacent catalog versions to detect
score-instability across small data edits.

---

## Reflection

The graded responsible-AI reflection — how I collaborated with AI on
this project, one helpful and one flawed AI suggestion, and the
system's honest limitations — lives in
[`model_card.md`](model_card.md).

---

## Repository map

```
├── README.md                       ← this file
├── model_card.md                   ← reflection + limitations + AI collaboration
├── ai_interactions.md              ← older per-challenge log from the base project
├── requirements.txt
├── evaluation_report.md            ← generated by src/evaluation.py
├── evaluation_report.json          ← same, machine-readable
├── assets/
│   ├── sample_run.txt              ← full stdout of src/main.py (256 lines)
│   └── sample_run_trace.txt        ← stderr log trace for the same run
├── diagrams/
│   └── architecture.mmd            ← Mermaid source
├── data/
│   └── songs.csv                   ← 18 songs × 15 features
├── src/
│   ├── main.py                     ← agent-driven demo entry point
│   ├── agent.py                    ← plan → act → critique → refine loop
│   ├── query_parser.py             ← NL → UserProfile using the KB
│   ├── critic.py                   ← structured findings + confidence
│   ├── evaluation.py               ← reliability harness (cases + criteria)
│   ├── logger.py                   ← structured JSON logging
│   ├── recommender.py              ← original scoring engine (unchanged core)
│   └── kb/
│       └── music_terms.md          ← retrieval knowledge base
└── tests/
    ├── test_recommender.py         ← 2 legacy tests (scorer + dataclasses)
    └── test_agent.py               ← 13 new tests (parser, critic, agent, harness)
```

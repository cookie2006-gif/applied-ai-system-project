# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeMatch 1.0** — a transparent, points-based music recommender.

---

## 2. Intended Use

VibeMatch takes a small "taste profile" (favorite genre, favorite mood, a target energy level from 0 to 1, and whether the user likes acoustic textures) and returns five songs from an 18-song catalog with a plain-English reason for each pick. It's designed as a **classroom exercise** — a tiny, readable recommender you can trace end-to-end to understand how scoring, ranking, and explanation work.

**Assumptions about the user.** The user can describe their taste using four fields. There is no listening history, no thumbs-up/thumbs-down feedback loop, and no notion of time-of-day or context.

**What this is not for.** This is not a production recommender. It should not be used to serve real listeners, to personalize a real music service, to evaluate artist popularity, or to make any decision that affects a real user's experience. The catalog is 18 hand-authored rows; the scoring weights were chosen by hand, not learned from data.

---

## 3. How the Model Works

Each song in the catalog has a genre, a mood, and a few numbers between 0 and 1 that describe the audio (energy, valence, danceability, acousticness). Each user profile is described in the same shape.

The recommender walks the catalog one song at a time and awards points:

- **+2 points** if the song's genre exactly matches the user's favorite. **+1 point** if it's a close cousin (for example, indie pop when the user asked for pop).
- **+1 point** if the mood exactly matches. **+0.5 point** if the mood is a close cousin.
- **Up to +2 points** based on how close the song's energy is to the user's target. A perfect match gets the full 2 points; further away means fewer points, all the way down to zero.
- **Up to +1 point** if the song's acoustic texture matches the user's preference (either "I like acoustic" or "I don't").
- **A small extra bonus** (up to +0.5 point) if the user is in an upbeat mood and the song is high in valence and danceability.

Once every song has a score, the recommender sorts the list highest-first and returns the top five, along with the list of reasons each song earned its points. If two songs tie, the one with the stronger genre match wins first, then the one with the closer energy, then the one with the lower song id — so the same profile always returns the same list.

---

## 4. Data

The catalog is a single CSV file (`data/songs.csv`) with **18 songs**, all hand-authored for this exercise.

- **Columns:** `id`, `title`, `artist`, `genre`, `mood`, `energy`, `tempo_bpm`, `valence`, `danceability`, `acousticness`.
- **Genres represented (15):** pop, indie pop, lofi, rock, ambient, jazz, synthwave, hip hop, classical, edm, folk, r&b, metal, reggae, country.
- **Moods represented (14):** happy, chill, intense, relaxed, moody, focused, energetic, melancholy, euphoric, nostalgic, romantic, aggressive, hopeful, wistful.
- **What I added.** The starter came with 10 songs across 7 genres. I added 8 new songs to introduce 8 fresh genres and 8 fresh moods, so the neighbor tables and adversarial profiles have something to hit.
- **What's missing.** No lyrics or language. No actual audio — every feature is a hand-picked number, not a measurement. No popularity or play-count signal. No listener history. No release-date or era information. And with only 18 songs, every genre outside pop and lofi has just one or two entries, which caps how much variety the recommender can offer even when the scoring works correctly.

---

## 5. Strengths

- **Handles the extremes cleanly.** Profiles at opposite ends of the vibe map (chill lofi vs. deep intense rock) produce visibly different top-5 lists with no overlap. Every scoring component pulls in the same direction, so the separation is large and stable.
- **Every recommendation comes with a plain reason.** The output lists each component's point contribution (e.g. `matched genre (pop) [+2.00]; energy 0.82 vs target 0.85 [+1.94]`) so a reader can see exactly why a song was picked. Nothing is hidden inside a black box.
- **Deterministic and testable.** Same profile in, same list out. Explicit tie-breakers (genre → energy → id) mean the output is stable across runs, which makes automated tests straightforward.
- **Neighbor tables prevent brittle cliffs.** A user asking for pop still sees indie pop, synthwave, and edm songs in their results — the +1.0 "related genre" bonus gives the ranking a graceful falloff instead of a hard yes/no gate.
- **Small enough to read end-to-end.** Every function that touches a song's score lives in one file, under 250 lines. A student can trace a single song from the CSV through scoring to output without losing track.

---

## 6. Limitations and Bias

The biggest weakness I found during stress-testing is a **genre filter bubble caused by the small catalog**. The recipe awards +2.0 for an exact genre match, but the catalog only has 18 songs spread across 15 genres — so any genre with a single entry (rock, ambient, jazz, metal, reggae, r&b, hip hop, folk, country, classical, edm) can *only* be recommended to a user whose profile matches it exactly or falls into its narrow neighbor family. A "chill classical" user, for example, gets *Winter Prelude* at #1 and then falls straight into the ambient/lofi cluster, because there is no second classical song. **The recommender's diversity is a hard cap on the catalog's diversity, not something the algorithm can create.**

Two related biases fall out of this. First, **pop and lofi are structurally advantaged** — pop has 2 direct entries plus 3 neighbors (indie pop, synthwave, edm) and lofi has 3 direct entries, so users with those preferences see richer top-5 lists than a user asking for "metal" or "reggae." Second, **the system has no negative preferences** — it can reward "likes_acoustic=True" but can't penalize a genre the user actively dislikes. A metalhead who happens to say `likes_acoustic=True` still gets metal ranked #1 because acoustic points only add up to +1.0, which can't overcome a +2.0 genre match. In effect, the recipe treats every user as a "yes-and" listener, never a "no-thanks" one, which will unintentionally over-serve users whose preferences happen to line up cleanly with what's in the catalog.

---

## 7. Evaluation

I evaluated the recommender against six user profiles — three "sensible" personas and three adversarial ones designed to trip the scoring logic. Full terminal output for each is in the README's *Experiments You Tried* section; the summary and comparisons below are what I looked for and what surprised me.

**Profiles tested.** Sensible: *High-Energy Pop* (`pop / happy / 0.85 / False`), *Chill Lofi Study* (`lofi / focused / 0.40 / True`), *Deep Intense Rock* (`rock / intense / 0.90 / False`). Adversarial: *Sad but Hyped* (`indie pop / melancholy / 0.90` — mood contradicts energy), *Metalhead Who Wants Acoustic* (`metal / aggressive / 0.95 / True` — genre contradicts acoustic pref), *Unknown Genre* (`k-pop / happy / 0.70` — genre isn't in the catalog or neighbor graph).

**What I looked for.** (1) Do the top picks match what a real listener would expect? (2) Does the same song keep showing up at #1 across different profiles — which would suggest the genre weight is too strong? (3) Do the adversarial profiles produce visibly worse or oddly-mixed results that expose scoring blind spots?

**What surprised me.** Two things. First, in the *Chill Lofi Study* output, *Library Rain* and *Midnight Coding* are numerically almost indistinguishable (5.26 vs. 5.17). The scoring recipe technically ranks them but the "reason" behind the ordering is a 0.05 energy difference, which is well below what a human ear would call meaningful. Second, the *Sad but Hyped* adversarial profile still returned *Rooftop Lights* (mood: happy) at #1 — the +2.0 genre match completely swamped the missing mood match. I expected the mood mismatch to demote it further; it didn't, which is real evidence the +2.0 genre weight might be over-tuned.

**Cross-profile comparisons.**

- **High-Energy Pop vs. Chill Lofi Study.** Complete inversion, as expected. Pop profile gets loud, high-energy, produced tracks (energy 0.75–0.95, acousticness < 0.35); lofi profile gets calm, acoustic-forward tracks (energy 0.28–0.42, acousticness > 0.70). The recipe cleanly separates the two "vibe hemispheres." Every scoring component pulls in the same direction, so the gap between the two rankings is large and stable.

- **Chill Lofi Study vs. Deep Intense Rock.** These are the extremes — one is calm and acoustic, the other is loud and electric. What's interesting is that the *Deep Intense Rock* top-5 becomes much thinner: *Storm Runner* at 5.88 is followed by a big drop to *Iron Requiem* at 4.32 and then a steeper drop from there. That's because the catalog only has one rock song and one metal song; the recommender has to reach into hip hop and synthwave to fill positions 3–5. Meanwhile the lofi top-5 stays tightly clustered (5.78 → 4.18) because the lofi/jazz/ambient family is well-represented.

- **High-Energy Pop vs. Sad but Hyped.** Same target energy (0.85 vs 0.90), same "upbeat-ish" catalog, different declared mood. But the top result stays in the same pop/indie-pop cluster because *genre dominates mood* — the mood swap didn't reorganize the rankings the way I expected. This is exactly the "over-prioritizes genre" bias called out in Section 6.

- **Deep Intense Rock vs. Metalhead Who Wants Acoustic.** These profiles have almost identical numeric preferences (energy 0.90 vs 0.95, both intense-family moods, both distortion-heavy genres) but the metalhead flips `likes_acoustic` to True. The ranking is *nearly identical* — *Storm Runner* and *Iron Requiem* stay at the top — because rock and metal both have acousticness under 0.15, so the acoustic component contributes almost nothing either way. The system silently ignored the contradiction rather than flagging it. That's a scoring gap worth fixing.

- **Unknown Genre vs. High-Energy Pop.** These share the same mood ("happy") and similar energy (0.70 vs 0.85), but the genre is unrecognized. The top-5 becomes a "best available" mood/energy match — *Sunrise City* still leads, but now on mood+energy alone rather than mood+energy+genre. That's arguably the right fallback (no crash, no empty list), but a real system should tell the user "we don't have your genre" rather than silently substitute.

**In plain language.** Why does *Gym Hero* keep showing up for a "Happy Pop" user? Because *Gym Hero* is a pop song (worth 2 points) with high energy close to the target (worth almost 2 more points) and no acoustic guitars (worth almost 1 point) — the only thing it's missing is the "happy" mood label. It lost 1 point on mood but still stacked up almost 5 points from everything else, and there just aren't many pop songs in this small catalog for it to compete with. To make *Gym Hero* stop appearing, you'd either need more pop-happy songs in the data, or you'd need to make the mood mismatch penalty bigger than 1 point.

---

## 8. Future Work

If I kept developing this, the top three changes would be:

1. **Multi-genre and negative preferences.** Replace the single `favorite_genre` string with a small list of allowed genres and a small list of *disliked* genres. Right now the recipe can only reward what the user says they want; it has no way to demote a song a user actively wouldn't play. Adding a "-1.0 disliked genre" bucket would fix the metalhead-loves-acoustic edge case and stop pop from being over-served.
2. **Continuous `acousticness` target instead of a boolean.** Change `likes_acoustic: bool` to `target_acousticness: float` and score by closeness, the same way `energy` is scored today. A boolean flip is too coarse — most listeners want a moderate texture, not one extreme or the other.
3. **Context field on the user profile.** Add something like `context: "studying" | "commuting" | "workout" | "relaxing"` and use it to break the near-ties that currently happen between `chill`, `focused`, and `relaxed`. The mood column can't distinguish those on its own because they map to nearly identical numeric neighborhoods; a context tag would.

Nice-to-have follow-ups: grow the catalog so every genre has 3+ entries (removes the small-catalog filter bubble), add a diversity re-ranker to prevent two songs by the same artist from appearing back-to-back, and let the user tune the weights themselves via a small slider config so they can experiment with what "match" means to them personally.

---

## 9. Personal Reflection

**Biggest learning moment.** The point where it clicked for me was realizing that "recommendation" is really two problems stacked on top of each other. There's the **scoring** problem — how do I judge a single song against a single user — and there's the **ranking** problem — how do I turn a bunch of scores into an ordered list I can actually show. I kept trying to solve them together at first, and my code got tangled. Once I split them into `score_song` (judges one song, knows nothing about the others) and `recommend_songs` (sorts the results, adds tie-breakers), everything got simpler. That mental split is probably the most reusable thing I'll take away from this project.

**How AI tools helped, and when I had to double-check.** Getting the CSV loader, the dataclasses, and the docstrings written was fast — the assistant produced clean scaffolding I could edit rather than build from a blank page. Where I had to slow down was on **anything involving specific numbers**. When I ran the weight-shift experiment (2× energy, 0.5× genre), I had a hunch about what would happen, and so did the assistant — but the actual output *disagreed with both of us*. *Sunrise City* held #1 instead of getting displaced by *Gym Hero* like I predicted; *Iron Requiem* and *Storm Runner* didn't crash the top-5 the way I thought they would. That was a real reminder that AI is great at generating plausible-looking code and plausible-sounding predictions, but the plausible answer isn't the same as the correct one. If the number matters, I have to run the code, not trust the guess.

**What surprised me about "simple" algorithms.** I expected a hand-tuned points system to feel obviously mechanical, and to some degree it does — the tie between *Library Rain* and *Midnight Coding* (5.26 vs. 5.17) is basically arbitrary. But the top-3 for each persona actually feels intentional. When you read "matched genre (lofi) [+2.00]; matched mood (focused) [+1.00]; energy 0.40 vs target 0.40 [+2.00]; acoustic-forward texture [+0.78]" underneath *Focus Flow*, it reads like a person thought about it. There's no ML in this. The system doesn't know anything about music. It just adds numbers according to five rules I wrote by hand — and that's enough to produce lists that a listener would recognize as *reasonable*. That was the surprising part: the gap between "obviously mechanical" and "feels curated" is much smaller than I would have guessed.

**What I'd try next.** Two things. First, wire up a real audio-feature API (Spotify's, or one of the open-source alternatives) so the catalog isn't hand-authored — that would immediately expose which of my biases came from the recipe and which came from the tiny dataset. Second, add a small collaborative-filtering signal on top: even a crude "users who liked X also liked Y" table would let the system recommend things the content-based scorer would never find on its own. That combination — content-based transparency plus collaborative signal for discovery — is basically what real systems do, and I'd like to see how it feels to build it end-to-end at a scale where I can actually observe the tradeoffs.

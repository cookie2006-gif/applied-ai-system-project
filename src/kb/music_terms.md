# Music-Domain Knowledge Base

The query parser (`src/query_parser.py`) does a lightweight retrieval pass over
this document at import time. Each fenced block below is a "chunk" the parser
looks up when it maps a free-form natural-language request to a structured
`UserProfile`.

Chunks are simple key → value mappings. The parser tokenizes the user's
query, matches tokens against the `triggers:` field of each chunk, and uses
the first match to populate the corresponding profile field. This is a
tiny, deterministic, dependency-free stand-in for a real embedding-based
retriever — enough to demonstrate how a NL layer wraps the scoring engine
without requiring an external LLM.

## Genre triggers

```kb
field: genre
- pop           triggers: pop, popmusic, top40
- indie pop     triggers: indie, indiepop, alternative
- lofi          triggers: lofi, lo-fi, lo fi, chillhop, chill beats, study beats
- rock          triggers: rock, classic rock, alt rock
- metal         triggers: metal, heavy, thrash, doom
- jazz          triggers: jazz, bebop, swing
- ambient       triggers: ambient, atmospheric, drone
- classical     triggers: classical, orchestral, symphonic, piano
- synthwave     triggers: synthwave, retrowave, 80s
- edm           triggers: edm, electronic, dance, house, techno
- hip hop       triggers: hip hop, hiphop, rap
- r&b           triggers: r&b, rnb, soul
- folk          triggers: folk, singer-songwriter, acoustic guitar
- country       triggers: country, americana
- reggae        triggers: reggae, dub, ska
```

## Mood triggers

```kb
field: mood
- happy         triggers: happy, cheerful, joy, bright, uplifting
- chill         triggers: chill, mellow, laid back, laidback, easy
- focused       triggers: focused, study, studying, concentrate, deep work
- relaxed       triggers: relaxed, unwind, decompress
- moody         triggers: moody, dark
- melancholy    triggers: sad, melancholy, blue
- intense       triggers: intense, powerful, driving
- aggressive    triggers: aggressive, hard, brutal
- energetic     triggers: energetic, hype, pumped, fired up, upbeat
- euphoric      triggers: euphoric, festival, peak, drop
- nostalgic     triggers: nostalgic, throwback, old school
- wistful       triggers: wistful, longing, bittersweet
- hopeful       triggers: hopeful, sunny, warm
- romantic      triggers: romantic, love, date, intimate
```

## Energy triggers

```kb
field: energy
- 0.90          triggers: high energy, workout, gym, running, sprint, intense
- 0.75          triggers: upbeat, driving, party
- 0.55          triggers: moderate, mid energy, walking
- 0.40          triggers: chill, study, focus, calm, mellow
- 0.20          triggers: low energy, sleep, background, meditation, wind down
```

## Context / activity triggers (drive `extra_mood_tags`)

```kb
field: extra_mood_tags
- studying|focused|calm     triggers: study, studying, homework, coding, deep work
- driving|adrenaline        triggers: driving, drive, road trip
- pumping|motivational      triggers: workout, gym, lifting, running
- rainy|cozy                triggers: rainy day, rain, cozy, coffee shop
- dreamy|expansive          triggers: sleep, meditation, dreaming
- festival|peak-hour        triggers: festival, party, club, drop
```

## Acoustic-preference triggers

```kb
field: likes_acoustic
- true          triggers: acoustic, unplugged, singer-songwriter, guitar, piano, natural
- false         triggers: electric, produced, synth, digital, edm, pop, dance
```

## Instrumental-preference triggers

```kb
field: prefers_instrumental
- true          triggers: instrumental, no vocals, no lyrics, background
- false         triggers: with vocals, with lyrics, singing
```

## Popularity-preference triggers

```kb
field: popularity_preference
- popular       triggers: mainstream, popular, top hits, chart
- obscure       triggers: obscure, hidden gem, underground, indie, deep cut
- any           triggers: (default)
```

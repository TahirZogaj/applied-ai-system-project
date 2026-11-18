# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

My version, **VibeMatch 1.0**, is a content-based recommender that runs in the terminal. It loads a 20-song catalog, scores every song against a user's favorite genre, favorite mood, target energy and acoustic preference, and prints the top 5 with the reasons behind each score. I tested it with 7 user profiles, including 4 edge cases designed to trick it, ran a weight-shift experiment, and documented its biases in the [model card](model_card.md).

---

## How The System Works

Real-world platforms like Spotify and YouTube combine two approaches. **Collaborative filtering** recommends what similar users liked, based on behavior such as likes, skips, replays and playlist adds. **Content-based filtering** recommends songs whose attributes, such as genre, mood, tempo and energy, resemble what the user already enjoys. These systems usually work in two stages: they first gather candidate songs, then rank them with a model that predicts what the user will engage with. My version is a small **content-based** recommender, because the dataset has song attributes but no listening history from other users. It prioritizes **genre first, then mood, then how close a song's energy is to the user's target**, so it favors songs that match the user's overall "vibe" rather than simply the loudest or calmest songs.

### Features used

**`Song`**
- `genre`: compared to the user's favorite genre (exact match)
- `mood`: compared to the user's favorite mood (exact match)
- `energy` (0–1): compared to the user's target energy by closeness
- `acousticness` (0–1): used as a small tiebreaker based on the user's acoustic preference
- `title`, `artist`: shown in results and explanations
- Loaded but not scored: `tempo_bpm`, `danceability` and `valence`. Tempo and danceability are strongly correlated with energy in this dataset (0.96 and 0.86), so scoring them would count the same signal twice.

**`UserProfile`**
- `favorite_genre`: e.g. `"pop"`
- `favorite_mood`: e.g. `"happy"`
- `target_energy`: e.g. `0.8`
- `likes_acoustic`: `True` / `False`

### Algorithm recipe

**Scoring rule (one song):**

| Rule | Points |
|---|---|
| Genre matches `favorite_genre` | +2.0 |
| Mood matches `favorite_mood` | +1.0 |
| Energy closeness: `1 − abs(song.energy − target_energy)` | up to +1.0 |
| Acoustic fit: `acousticness` if `likes_acoustic`, else `1 − acousticness` | up to +0.5 |

The maximum score is 4.5. Each rule that adds points also records a reason, such as "genre match (+2.0)", so every recommendation can be explained.

**Ranking rule (list of songs):** score every song, sort from highest to lowest score, and return the top `k`.

```
UserProfile + songs.csv → score each song → sort by score → top k + reasons
```

### Dataset and example profile

`data/songs.csv` was expanded from 10 to **20 songs** (17 genres, 16 moods). The new songs add genres and moods that were missing, such as metal, classical, folk, sad and angry, and include low-valence (dark) songs.

`src/main.py` runs seven profiles (see **Stress Test Results**). The default is an upbeat **pop/happy** listener:

```python
{"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.80, "likes_acoustic": False}
```

The second is a "late-night study" **lofi/chill** listener:

```python
{"favorite_genre": "lofi", "favorite_mood": "chill", "target_energy": 0.40, "likes_acoustic": True}
```

Expected top 3 for lofi/chill: **Library Rain** (4.38), **Midnight Coding** (4.33), **Focus Flow** (3.39).

### Expected biases and limitations

- **Over-prioritizes genre.** A genre match (+2.0) is worth twice a mood match, so a same-genre song with the wrong mood can outrank a song that fits the mood perfectly. For a pop/happy user, "Gym Hero" (pop, *intense*) is expected to rank above "Rooftop Lights" (indie pop, *happy*).
- **Exact string matching is strict.** "indie pop" gets no credit for "pop", and "relaxed" or "peaceful" get no credit for "chill", even though they feel similar.
- **Sparse genres create a score cliff.** Most genres have only one song, so after the genre matches run out, the remaining songs are separated by tiny differences in energy and can be nearly tied.
- **No happy-vs-dark signal.** Valence isn't scored, so for a high-energy user, angry metal and festive Latin music score about the same.
- **Energy dominates the numeric score.** Energy, tempo, danceability and acousticness are highly correlated in this dataset, so the system mostly sees one dimension: calm vs intense.
- **Small, hand-made catalog.** 20 songs with made-up values reflect the dataset author's judgment about each genre's "typical" sound, not real listening data.

---

## Stress Test Results

`src/main.py` runs seven profiles: three core listener types and four adversarial or edge-case profiles designed to trick the scoring logic. The output for each profile is below, followed by what it shows.

### High-Energy Pop

```
================================================================
Profile: High-Energy Pop
  genre=pop  mood=happy  energy=0.80  acoustic=False
================================================================
1. Sunrise City — Neon Echo
   Score: 4.39 / 4.50   (pop, happy)
     • genre match: pop (+2.0)
     • mood match: happy (+1.0)
     • energy 0.82 vs target 0.80 (+0.98)
     • non-acoustic fit (+0.41)

2. Gym Hero — Max Pulse
   Score: 3.35 / 4.50   (pop, intense)
     • genre match: pop (+2.0)
     • energy 0.93 vs target 0.80 (+0.87)
     • non-acoustic fit (+0.47)

3. Rooftop Lights — Indigo Parade
   Score: 2.29 / 4.50   (indie pop, happy)
     • mood match: happy (+1.0)
     • energy 0.76 vs target 0.80 (+0.96)
     • non-acoustic fit (+0.33)

4. Concrete Crown — Mic Atlas
   Score: 1.44 / 4.50   (hip hop, confident)
     • energy 0.78 vs target 0.80 (+0.98)
     • non-acoustic fit (+0.46)

5. Storm Runner — Voltline
   Score: 1.34 / 4.50   (rock, intense)
     • energy 0.91 vs target 0.80 (+0.89)
     • non-acoustic fit (+0.45)
```

Works as expected. Sunrise City is the only pop + happy song. Gym Hero (pop, *intense*) beats Rooftop Lights (indie pop, *happy*) because genre (+2.0) outweighs mood (+1.0).

### Chill Lofi

```
================================================================
Profile: Chill Lofi
  genre=lofi  mood=chill  energy=0.40  acoustic=True
================================================================
1. Library Rain — Paper Lanterns
   Score: 4.38 / 4.50   (lofi, chill)
     • genre match: lofi (+2.0)
     • mood match: chill (+1.0)
     • energy 0.35 vs target 0.40 (+0.95)
     • acoustic fit (+0.43)

2. Midnight Coding — LoRoom
   Score: 4.33 / 4.50   (lofi, chill)
     • genre match: lofi (+2.0)
     • mood match: chill (+1.0)
     • energy 0.42 vs target 0.40 (+0.98)
     • acoustic fit (+0.35)

3. Focus Flow — LoRoom
   Score: 3.39 / 4.50   (lofi, focused)
     • genre match: lofi (+2.0)
     • energy 0.40 vs target 0.40 (+1.00)
     • acoustic fit (+0.39)

4. Spacewalk Thoughts — Orbit Bloom
   Score: 2.34 / 4.50   (ambient, chill)
     • mood match: chill (+1.0)
     • energy 0.28 vs target 0.40 (+0.88)
     • acoustic fit (+0.46)

5. Coffee Shop Stories — Slow Stereo
   Score: 1.42 / 4.50   (jazz, relaxed)
     • energy 0.37 vs target 0.40 (+0.97)
     • acoustic fit (+0.45)
```

Works as expected. All three lofi songs fill the top 3. Spacewalk Thoughts (ambient, chill) is the best non-lofi pick thanks to its mood match.

### Deep Intense Rock

```
================================================================
Profile: Deep Intense Rock
  genre=rock  mood=intense  energy=0.90  acoustic=False
================================================================
1. Storm Runner — Voltline
   Score: 4.44 / 4.50   (rock, intense)
     • genre match: rock (+2.0)
     • mood match: intense (+1.0)
     • energy 0.91 vs target 0.90 (+0.99)
     • non-acoustic fit (+0.45)

2. Gym Hero — Max Pulse
   Score: 2.44 / 4.50   (pop, intense)
     • mood match: intense (+1.0)
     • energy 0.93 vs target 0.90 (+0.97)
     • non-acoustic fit (+0.47)

3. Laser Rush — DJ Kinetic
   Score: 1.43 / 4.50   (edm, energetic)
     • energy 0.95 vs target 0.90 (+0.95)
     • non-acoustic fit (+0.48)

4. Iron Furnace — Grave Signal
   Score: 1.42 / 4.50   (metal, angry)
     • energy 0.97 vs target 0.90 (+0.93)
     • non-acoustic fit (+0.48)

5. Fuego en la Pista — Los Caminantes
   Score: 1.36 / 4.50   (latin, festive)
     • energy 0.86 vs target 0.90 (+0.96)
     • non-acoustic fit (+0.40)
```

#1 is clearly right, but after the single rock song the list is effectively a tie: ranks 3–5 (EDM, metal, Latin) are within 0.07 of each other and are separated only by energy. A festive Latin song ranks right next to angry metal, because nothing in the score measures happy vs dark.

### EDGE: Sad but Hyped

```
================================================================
Profile: EDGE: Sad but Hyped
  genre=edm  mood=sad  energy=0.90  acoustic=False
================================================================
1. Laser Rush — DJ Kinetic
   Score: 3.43 / 4.50   (edm, energetic)
     • genre match: edm (+2.0)
     • energy 0.95 vs target 0.90 (+0.95)
     • non-acoustic fit (+0.48)

2. Gym Hero — Max Pulse
   Score: 1.44 / 4.50   (pop, intense)
     • energy 0.93 vs target 0.90 (+0.97)
     • non-acoustic fit (+0.47)

3. Storm Runner — Voltline
   Score: 1.44 / 4.50   (rock, intense)
     • energy 0.91 vs target 0.90 (+0.99)
     • non-acoustic fit (+0.45)

4. Iron Furnace — Grave Signal
   Score: 1.42 / 4.50   (metal, angry)
     • energy 0.97 vs target 0.90 (+0.93)
     • non-acoustic fit (+0.48)

5. Empty Train Station — Hollow Pines
   Score: 1.39 / 4.50   (folk, sad)
     • mood match: sad (+1.0)
     • energy 0.24 vs target 0.90 (+0.34)
     • non-acoustic fit (+0.05)
```

**The conflict is resolved in favor of energy.** The only sad song in the catalog (Empty Train Station) barely makes #5, because its low energy costs it more than the mood match earns. The other picks are intense or upbeat songs; Gym Hero is actually a cheerful track (valence 0.77). Valence isn't scored, so the system has no way to find "energetic *and* sad" music.

### EDGE: Acoustic Headbanger

```
================================================================
Profile: EDGE: Acoustic Headbanger
  genre=metal  mood=angry  energy=0.95  acoustic=True
================================================================
1. Iron Furnace — Grave Signal
   Score: 4.00 / 4.50   (metal, angry)
     • genre match: metal (+2.0)
     • mood match: angry (+1.0)
     • energy 0.97 vs target 0.95 (+0.98)
     • acoustic fit (+0.01)

2. Laser Rush — DJ Kinetic
   Score: 1.02 / 4.50   (edm, energetic)
     • energy 0.95 vs target 0.95 (+1.00)
     • acoustic fit (+0.02)

3. Storm Runner — Voltline
   Score: 1.01 / 4.50   (rock, intense)
     • energy 0.91 vs target 0.95 (+0.96)
     • acoustic fit (+0.05)

4. Fuego en la Pista — Los Caminantes
   Score: 1.01 / 4.50   (latin, festive)
     • energy 0.86 vs target 0.95 (+0.91)
     • acoustic fit (+0.10)

5. Gym Hero — Max Pulse
   Score: 1.01 / 4.50   (pop, intense)
     • energy 0.93 vs target 0.95 (+0.98)
     • acoustic fit (+0.03)
```

**The acoustic preference has almost no effect.** High-energy songs are never acoustic in this catalog, so the acoustic bonus is 0.01–0.10 for every top result. Ranks 2–5 are all 1.01–1.02, so their order is decided by tiny rounding differences and CSV order, not by real preference.

### EDGE: Ghost Genre

```
================================================================
Profile: EDGE: Ghost Genre
  genre=k-pop  mood=euphoric  energy=0.50  acoustic=False
================================================================
1. Velvet After Hours — Sienna Rae
   Score: 1.26 / 4.50   (r&b, romantic)
     • energy 0.55 vs target 0.50 (+0.95)
     • non-acoustic fit (+0.31)

2. Concrete Crown — Mic Atlas
   Score: 1.18 / 4.50   (hip hop, confident)
     • energy 0.78 vs target 0.50 (+0.72)
     • non-acoustic fit (+0.46)

3. Island Breeze Riddim — Kofi Sunrise
   Score: 1.18 / 4.50   (reggae, uplifting)
     • energy 0.60 vs target 0.50 (+0.90)
     • non-acoustic fit (+0.28)

4. Night Drive Loop — Neon Echo
   Score: 1.14 / 4.50   (synthwave, moody)
     • energy 0.75 vs target 0.50 (+0.75)
     • non-acoustic fit (+0.39)

5. Dusty Porch Swing — Willow Creek Band
   Score: 1.11 / 4.50   (country, nostalgic)
     • energy 0.52 vs target 0.50 (+0.98)
     • non-acoustic fit (+0.13)
```

**No error and no warning.** When the genre and mood don't exist in the catalog, the system quietly falls back to ranking by energy alone. It still presents 5 "recommendations", but the best score is only 1.26 / 4.50, and the user isn't told that nothing really matched.

### EDGE: Out-of-Range Energy

```
================================================================
Profile: EDGE: Out-of-Range Energy
  genre=classical  mood=peaceful  energy=1.50  acoustic=True
================================================================
1. Moonlit Sonata No. 2 — Clara Voss
   Score: 3.16 / 4.50   (classical, peaceful)
     • genre match: classical (+2.0)
     • mood match: peaceful (+1.0)
     • energy 0.18 vs target 1.50 (+-0.32)
     • acoustic fit (+0.48)

2. Iron Furnace — Grave Signal
   Score: 0.48 / 4.50   (metal, angry)
     • energy 0.97 vs target 1.50 (+0.47)
     • acoustic fit (+0.01)

3. Laser Rush — DJ Kinetic
   Score: 0.47 / 4.50   (edm, energetic)
     • energy 0.95 vs target 1.50 (+0.45)
     • acoustic fit (+0.02)

4. Storm Runner — Voltline
   Score: 0.46 / 4.50   (rock, intense)
     • energy 0.91 vs target 1.50 (+0.41)
     • acoustic fit (+0.05)

5. Fuego en la Pista — Los Caminantes
   Score: 0.46 / 4.50   (latin, festive)
     • energy 0.86 vs target 1.50 (+0.36)
     • acoustic fit (+0.10)
```

**Bug found: negative points.** A target energy of 1.5 is outside the valid 0–1 range, but it isn't rejected. The energy rule then gives Moonlit Sonata **−0.32** points (shown as `+-0.32`). The genre and mood matches still keep it at #1, but the input should be validated or clamped to 0–1.

### Summary of findings

| Profile | What it tests | Result |
|---|---|---|
| High-Energy Pop | Normal use | ✅ Sensible; genre bias visible at #2/#3 |
| Chill Lofi | Normal use | ✅ Sensible |
| Deep Intense Rock | Normal use | ⚠️ Correct #1, near-ties after it |
| Sad but Hyped | Conflicting mood vs energy | ⚠️ Energy wins; the sad song barely makes the list |
| Acoustic Headbanger | Conflicting acoustic vs energy | ⚠️ Acoustic preference is ignored in practice |
| Ghost Genre | Genre/mood not in catalog | ⚠️ Silent fallback to energy only |
| Out-of-Range Energy | Invalid input | ❌ Negative points; input isn't validated |

---

## Getting Started

### Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # macOS / Linux / Git Bash
   .\.venv\Scripts\Activate.ps1     # Windows PowerShell
   ```

2. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Add your Gemini API key (free at https://aistudio.google.com/apikey):

   ```bash
   cp .env.example .env
   # then edit .env and set GEMINI_API_KEY=...
   ```

   Without a key the app still runs in **offline mode** (keyword parsing plus the rule-based scorer's explanations).

### Running the app

All commands run from the project root.

```bash
python -m src.main "chill songs for studying"   # one request
python -m src.main                              # interactive prompt
python -m src.main --offline "upbeat pop"       # skip Gemini
python -m src.main --verbose "gym music"        # show each pipeline step
python -m src.main --demo                       # original Module 3 profile demo
```

Every pipeline step is logged to `logs/assistant.log`.

### How the AI pipeline works

Source: [diagrams/architecture.mmd](diagrams/architecture.mmd). Solid arrows are data flow; dotted arrows are checking and logging.

```mermaid
%% System architecture: AI Music Recommender (RAG over the song catalog)
%% Solid arrows = data flow. Dotted arrows = checking / logging.
flowchart TD
    %% ---------------- INPUT ----------------
    subgraph INPUT["1 · Input"]
        USER(["👤 User<br/>plain-English request<br/>e.g. 'sad acoustic songs for a rainy day'"])
        CSV[("data/songs.csv<br/>20-song catalog")]
    end

    %% ---------------- PROCESS ----------------
    subgraph PROCESS["2 · Process (src/assistant.py)"]
        G1{"Guardrail<br/>validate request<br/>(empty / > 300 chars)"}
        PARSER["Parser (LLM)<br/>Gemini → taste profile JSON<br/>genre · mood · energy · acoustic"]
        KW["Keyword parser<br/>(fallback if Gemini fails)"]
        G2{"Guardrail<br/>clean profile<br/>clamp energy 0-1 · flag unknown genre/mood"}
        RETRIEVER["Retriever<br/>Module 3 scorer: score_song + recommend_songs<br/>→ top 8 candidate songs"]
        WEAK{"Weak match?<br/>top score < 2.0"}
        GENERATOR["Generator (LLM)<br/>Gemini picks ≤ 5 songs + reasons<br/>using ONLY the 8 candidates"]
        G3{"Guardrail<br/>grounding check<br/>every pick id must be a candidate"}
        TPL["Template answer<br/>(fallback: scorer's own reasons)"]
    end

    %% ---------------- OUTPUT ----------------
    subgraph OUTPUT["3 · Output (src/main.py)"]
        ANSWER(["Ranked picks + explanations<br/>+ warnings shown to the user"])
        ERR(["Error message"])
    end

    %% ---------------- CHECKING ----------------
    subgraph CHECKS["4 · Humans & testing check the AI"]
        REVIEW(["👤 User reviews picks & warnings<br/>and rephrases if they don't fit"])
        LOG[("logs/assistant.log<br/>every step, fallback, dropped id")]
        DEV(["👤 Developer reads logs & eval report<br/>tunes prompts, weights, guardrails"])
        CASES["👤 Human-written eval cases<br/>10 requests + expected genres/moods/energy"]
        EVAL[["Evaluator: src/evaluate.py<br/>hit@1 · precision · energy fit · grounding<br/>consistency · fallback rate vs. offline baseline"]]
        TESTS[["Tester: pytest<br/>guardrails, grounding, fallbacks<br/>(fake LLM, no API key)"]]
    end

    %% Data flow
    USER --> G1
    G1 -- invalid --> ERR
    G1 -- ok --> PARSER
    PARSER -- API error --> KW
    PARSER --> G2
    KW --> G2
    G2 --> RETRIEVER
    CSV --> RETRIEVER
    RETRIEVER --> WEAK
    WEAK -- "yes: add warning" --> GENERATOR
    WEAK -- no --> GENERATOR
    GENERATOR --> G3
    G3 -- "valid picks (invented ids dropped)" --> ANSWER
    G3 -- "no valid picks / API error" --> TPL
    TPL --> ANSWER

    %% Checking loops
    ANSWER -.-> REVIEW
    REVIEW -. new request .-> USER
    PARSER -.-> LOG
    RETRIEVER -.-> LOG
    G3 -.-> LOG
    CASES --> EVAL
    EVAL -. runs full pipeline .-> G1
    TESTS -. checks .-> PROCESS
    LOG -.-> DEV
    EVAL -. eval_report.json .-> DEV
    DEV -. improves .-> PROCESS
```

1. **Guardrail:** reject empty or oversized requests.
2. **Parse:** Gemini turns the request into a taste profile (genre, mood, energy, acoustic) using the catalog's own genre and mood vocabulary. If the call fails, a keyword parser is used instead.
3. **Guardrail:** clamp energy to 0-1, fix types, and warn when a genre or mood is not in the catalog.
4. **Retrieve:** the Module 3 scorer ranks all songs in `data/songs.csv` and keeps the top 8 candidates.
5. **Generate:** Gemini chooses and explains up to 5 picks, seeing **only** those 8 candidates.
6. **Guardrail:** any song id not in the retrieved candidates is dropped and logged. If no valid picks remain, the scorer's own explanations are used.

### Running tests and evaluation

```bash
pytest                          # unit tests (use a fake LLM, no API key needed)
python -m src.evaluate          # offline baseline vs. Gemini RAG on 10 requests
python -m src.evaluate --offline
```

The evaluation reports hit@1, precision (share of returned picks that fit), average number of picks, energy fit, grounding (no invented songs), weak-match flagging, consistency across repeated runs, and fallback rate. The full report is saved to `logs/eval_report.json`.

---

## Sample Recommendation Output

Output of `python -m src.main` for the default **pop/happy** profile:

```
Loaded songs: 20

================================================================
Profile: High-Energy Pop
  genre=pop  mood=happy  energy=0.80  acoustic=False
================================================================
1. Sunrise City — Neon Echo
   Score: 4.39 / 4.50   (pop, happy)
     • genre match: pop (+2.0)
     • mood match: happy (+1.0)
     • energy 0.82 vs target 0.80 (+0.98)
     • non-acoustic fit (+0.41)

2. Gym Hero — Max Pulse
   Score: 3.35 / 4.50   (pop, intense)
     • genre match: pop (+2.0)
     • energy 0.93 vs target 0.80 (+0.87)
     • non-acoustic fit (+0.47)

3. Rooftop Lights — Indigo Parade
   Score: 2.29 / 4.50   (indie pop, happy)
     • mood match: happy (+1.0)
     • energy 0.76 vs target 0.80 (+0.96)
     • non-acoustic fit (+0.33)

4. Concrete Crown — Mic Atlas
   Score: 1.44 / 4.50   (hip hop, confident)
     • energy 0.78 vs target 0.80 (+0.98)
     • non-acoustic fit (+0.46)

5. Storm Runner — Voltline
   Score: 1.34 / 4.50   (rock, intense)
     • energy 0.91 vs target 0.80 (+0.89)
     • non-acoustic fit (+0.45)
```

**Does this match expectations?** Mostly yes. Sunrise City is the only song that matches pop *and* happy, so it ranks #1 with a near-perfect score. Gym Hero (#2) beats Rooftop Lights (#3) because a genre match (+2.0) outweighs a mood match (+1.0), even though Rooftop Lights arguably fits a "happy" listener better. This is the genre bias predicted above. Ranks 4–5 have no genre or mood match and are ordered only by energy closeness.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

### Experiment 1: Weight shift (energy ×2, genre ×½)

**Change:** in `src/recommender.py`, `GENRE_WEIGHT` went from 2.0 to **1.0** and `ENERGY_WEIGHT` went from 1.0 to **2.0**. Mood (1.0) and acoustic (0.5) stayed the same.

**Is the math still valid?** Yes. The maximum score is still 1.0 + 1.0 + 2.0 + 0.5 = **4.5**, and for valid inputs (energy 0–1) every score stays between 0 and 4.5. The only exception is the existing out-of-range bug: with energy doubled, a target of 1.5 now produces **−0.64** energy points instead of −0.32.

**Top 5 before → after:**

| Profile | Baseline (genre 2.0, energy 1.0) | Experiment (genre 1.0, energy 2.0) |
|---|---|---|
| High-Energy Pop | Sunrise City, **Gym Hero, Rooftop Lights**, Concrete Crown, Storm Runner | Sunrise City, **Rooftop Lights, Gym Hero**, Concrete Crown, *Night Drive Loop* |
| Chill Lofi | Library Rain, Midnight Coding, Focus Flow, Spacewalk Thoughts, Coffee Shop Stories | *(same order)* |
| Deep Intense Rock | Storm Runner, Gym Hero, Laser Rush, Iron Furnace, Fuego en la Pista | *(same order)*; Storm Runner's lead over #2 shrank from 2.00 to 1.01 |
| Sad but Hyped | Laser Rush, Gym Hero, Storm Runner, Iron Furnace, **Empty Train Station** | Laser Rush, Storm Runner, Gym Hero, Iron Furnace, *Fuego en la Pista* (sad song dropped out) |
| Acoustic Headbanger | Iron Furnace, then near-ties | Iron Furnace, then near-ties in a different order |
| Ghost Genre | Velvet After Hours, Concrete Crown, Island Breeze, Night Drive Loop, Dusty Porch Swing | Velvet After Hours, *Dusty Porch Swing*, Island Breeze, *Midnight Bayou Blues*, *Midnight Coding* |
| Out-of-Range Energy | Moonlit Sonata (3.16) | Moonlit Sonata (**1.84**): the negative-points bug doubled |

**More accurate or just different?** Mostly **just different**, with one improvement and one regression:

- **#1 never changed.** In all 7 profiles, the song that matches genre, mood and energy still wins. The top pick is robust to this weight change.
- **Improvement:** for High-Energy Pop, the happy indie-pop song (Rooftop Lights) now beats the intense gym track (Gym Hero). That fits a "happy" listener better, and it reduces the genre bias noted earlier.
- **Regression:** for Sad but Hyped, the only sad song fell out of the top 5. With energy worth twice as much, its mood match can no longer make up for its low energy.
- **Ranks 3–5 are still near-ties.** They're now decided almost entirely by energy closeness, so the "loud, non-acoustic cluster" problem is stronger.

**Decision:** the baseline weights (genre 2.0, energy 1.0) were restored. The experiment shows that changing weights only reshuffles the middle of the list. The bigger problems (no valence, exact-match moods, small catalog) need new features or data, not different weights.

---

## Limitations and Risks

- **Tiny, made-up catalog.** There are only 20 songs, and 12 of the 17 genres have a single song, so most users get at most one genre match.
- **A "loud song" filter bubble.** After genre matches run out, energy decides the ranking, so high-energy users all get the same cluster of loud songs. Storm Runner appeared in 5 of 7 test profiles.
- **No happy-vs-dark signal.** Valence isn't scored, so a "sad but hyped" listener gets cheerful songs.
- **Strict exact matching.** "indie pop" isn't "pop", and "relaxed" isn't "chill".
- **Silent failures.** Unknown genres get low-confidence results with no warning, and an energy target above 1.0 produces negative points.
- **No understanding of lyrics, language, vocals or culture.**

See section 6 of the [model card](model_card.md) for details.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

How recommenders turn data into predictions

Building this project showed me that a recommender doesn't "understand" music. It turns each song into numbers and labels (genre, mood, energy, acousticness) and compares them to what the user says they like. My system gives points for each match: 2 for genre, 1 for mood, up to 1 for how close the energy is, and up to 0.5 for acoustic fit. Then it sorts every song by its total and shows the top five. The "prediction" is really a guess that a song with a high score is one the user will enjoy. I was surprised how convincing that felt: with only a few rules, my Chill Lofi profile got a list that looked like a real study playlist, and the printed reasons made each pick feel thoughtful.

Where bias or unfairness can show up

I also saw how easily bias slips in, even without anyone meaning it. Since 12 of my 17 genres had only one song, most users got at most one genre match, and the rest of their list was filled by whichever songs had the closest energy. That created a "loud song" bubble: Storm Runner appeared in 5 of my 7 test profiles. Users with less common tastes were treated worse. A "sad but hyped" listener got cheerful songs, because my system doesn't measure how happy or dark a song sounds. A k-pop fan got five confident-looking picks that matched nothing, with no warning. Even the choice to make genre worth twice as much as mood meant a happy-pop fan got an intense gym song ranked above a happy indie-pop song. In a real app with millions of songs and users, choices like these decide which artists get heard and which listeners get good recommendations, so the weights and the data need to be checked as carefully as the code.




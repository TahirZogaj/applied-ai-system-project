# 🎵 VibeMatch AI: A Grounded Music Recommender

Describe what you want to hear in plain English, like *"sad acoustic songs for a rainy day"*, and VibeMatch AI recommends songs from its catalog and explains each pick. It uses **retrieval-augmented generation (RAG)**: an LLM (Google Gemini) understands the request and writes the explanations, but it may only recommend songs that a deterministic retriever pulled from the catalog. Retrieval draws on **two sources**: the song catalog and a custom genre guide that explains which genres suit which activities and which genres the catalog lacks. Code-level guardrails check the output, so the AI cannot invent a song.

**Why it matters:** LLM-powered recommenders are useful because they understand vague, human requests ("music for the gym") that keyword systems can't. They are also prone to confidently recommending things that don't exist. This project shows one way to get the first without the second: keep the LLM on a short leash, check its output in code, log every step, and measure its quality against a simple baseline.

## Original Project (Module 3)

This project grows out of **VibeMatch 1.0, the Music Recommender Simulation** from Module 3. That version was a rule-based, content-based recommender. It loaded a 20-song catalog, scored each song against a fixed taste profile (favorite genre, favorite mood, target energy and acoustic preference) and printed the top 5 with the reason behind each score. Its goal was to show how recommenders turn data into rankings, and to stress-test the scoring rule with adversarial profiles and document its biases. The full Module 3 write-up is preserved in [docs/module3_vibematch_report.md](docs/module3_vibematch_report.md).

**What changed:** Module 3 needed a hand-built profile dictionary. VibeMatch AI takes free text, uses an LLM to understand it, keeps the Module 3 scorer as the retriever, and adds guardrails, logging, fallbacks and an evaluation harness.

## Architecture Overview

```mermaid
%% System architecture: VibeMatch AI (multi-source RAG: song catalog + genre guide)
%% Solid arrows = data flow. Dotted arrows = checking / logging.
flowchart TD
    %% ---------------- INPUT ----------------
    subgraph INPUT["1 · Input"]
        USER(["👤 User<br/>plain-English request<br/>e.g. 'sad acoustic songs for a rainy day'"])
        CSV[("data/songs.csv<br/>20-song catalog")]
        GUIDE[("data/genre_guide.md<br/>custom genre guide:<br/>activities, moods, missing genres")]
    end

    %% ---------------- PROCESS ----------------
    subgraph PROCESS["2 · Process (src/assistant.py)"]
        G1{"Guardrail<br/>validate request<br/>(empty / > 300 chars)"}
        GRET["Retriever #1: guide notes<br/>src/knowledge.py keyword match<br/>→ top 3 sections"]
        PARSER["Parser (LLM)<br/>Gemini → taste profile JSON<br/>genre · mood · energy · acoustic"]
        KW["Keyword parser<br/>(fallback if Gemini fails)"]
        G2{"Guardrail<br/>clean profile<br/>clamp energy 0-1 · flag unknown genre/mood"}
        RETRIEVER["Retriever #2: songs<br/>Module 3 scorer: score_song + recommend_songs<br/>→ top 8 candidate songs"]
        WEAK{"Weak match?<br/>top score < 2.0 or<br/>guide says genre missing"}
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
        CASES["👤 Human-written eval cases<br/>14 requests + expected genres/moods/energy"]
        EVAL[["Evaluator: src/evaluate.py<br/>hit@1 · precision · energy fit · grounding<br/>consistency · confidence · pass/fail<br/>with vs. without guide, LLM vs. offline"]]
        TESTS[["Tester: pytest<br/>guardrails, grounding, fallbacks<br/>(fake LLM, no API key)"]]
    end

    %% Data flow
    USER --> G1
    G1 -- invalid --> ERR
    G1 -- ok --> GRET
    GUIDE --> GRET
    GRET -- notes --> PARSER
    GRET -- notes --> GENERATOR
    GRET -- notes --> KW
    GRET -- missing genre --> WEAK
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
    G3 -- "LLM declines: keep its message,<br/>show closest songs labelled" --> ANSWER
    G3 -- "no valid picks / API error" --> TPL
    TPL --> ANSWER

    %% Checking loops
    ANSWER -.-> REVIEW
    REVIEW -. new request .-> USER
    GRET -.-> LOG
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

*Source: [diagrams/architecture.mmd](diagrams/architecture.mmd). Solid arrows are data flow; dotted arrows are checking and logging.*

A request moves through four stages:

1. **Input:** the user's request, plus two data sources: the song catalog (`data/songs.csv`) and the genre guide (`data/genre_guide.md`).
2. **Process** ([src/assistant.py](src/assistant.py)):
   - **Retriever #1, genre guide** ([src/knowledge.py](src/knowledge.py)): finds the 1-3 guide sections that match the request's activities and keywords ("coding" → lofi). Its notes are passed to both LLM steps and to the offline parser. If the request names a genre the catalog lacks, the guide triggers a warning.
   - **Parser (LLM):** Gemini converts the request into a structured taste profile (genre, mood, energy 0-1, acoustic yes/no), choosing from the catalog's own genre and mood vocabulary. If Gemini fails, a keyword parser takes over.
   - **Retriever #2, songs:** the original Module 3 scoring function ranks every song against that profile and keeps the top 8 candidates.
   - **Generator (LLM):** Gemini receives the request, the guide notes and only those 8 candidates, then picks up to 5 and writes a one-sentence reason and a confidence (0-1) for each. If nothing fits, it can decline, and its explanation is kept.
   - **Guardrails** sit between every step. They reject empty or oversized input, clamp invalid values, warn when a genre isn't in the catalog, flag weak matches, and drop any song ID that wasn't retrieved. If nothing valid remains, the app falls back to the scorer's own explanations.
3. **Output** ([src/main.py](src/main.py)): ranked picks, explanations and any warnings.
4. **Humans and testing:** the user reviews the warnings and can rephrase. Every step is logged to `logs/assistant.log` for the developer. `pytest` checks the guardrails, and [src/evaluate.py](src/evaluate.py) scores the whole pipeline against human-written test cases and compares it with an offline baseline.

## Setup Instructions

Requires **Python 3.10+**. Run all commands from the project root.

1. **Clone and enter the repo**
   ```bash
   git clone https://github.com/TahirZogaj/applied-ai-system-project.git
   cd applied-ai-system-project
   ```
2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate          # macOS / Linux / Git Bash
   .\.venv\Scripts\Activate.ps1       # Windows PowerShell
   ```
3. **Install dependencies**
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. **Add a Gemini API key.** Get a free key at https://aistudio.google.com/apikey, then:
   ```bash
   cp .env.example .env
   # edit .env and set GEMINI_API_KEY=your_key
   ```
   No key? Everything still runs in **offline mode**, using keyword parsing and the rule-based explanations.

   > **Privacy:** in online mode your request text is sent to Google's Gemini API, so don't include personal information. Requests are also logged locally to `logs/assistant.log`, which is git-ignored.
5. **Run it**
   ```bash
   python -m src.main "chill songs for studying"   # one request
   python -m src.main                              # interactive prompt
   python -m src.main --verbose "gym music"        # also print each pipeline step
   python -m src.main --offline "upbeat pop"       # skip Gemini
   python -m src.main --no-guide "music for coding" # songs-only retrieval (for comparison)
   python -m src.main --demo                       # original Module 3 profile demo
   ```
6. **Test and evaluate**
   ```bash
   pytest                         # 17 unit tests, no API key needed
   python -m src.evaluate         # 14 requests × 4 configurations (~9 min on the free tier)
   ```

## Sample Interactions

More reproducible output, including test results, a step-by-step pipeline trace, offline mode and the evaluation summary, is in [docs/execution_log.md](docs/execution_log.md). Per-case evaluation tables are in [docs/evaluation_results.md](docs/evaluation_results.md).

These are real outputs from `python -m src.main "<request>"` using `gemini-3.5-flash-lite`. The `profile (llm)` line shows how Gemini interpreted the request, and `answer: llm` confirms the picks came from Gemini and passed the grounding check.

**1. Activity-based request.** Gemini maps "study" to the *focused* mood and a low energy target:
```
Request: chill lofi beats to study to
  profile (llm): genre=lofi  mood=focused  energy=0.20  acoustic=False
================================================================
Here are the best lofi tracks from the catalog to help you stay focused and relaxed while you study.

1. Focus Flow — LoRoom  (lofi, focused, energy 0.40)
     With its focused mood and lofi genre, 'Focus Flow' is an ideal match for studying.
2. Midnight Coding — LoRoom  (lofi, chill, energy 0.42)
     'Midnight Coding' brings a chill lofi vibe that fits background study sessions well.
3. Library Rain — Paper Lanterns  (lofi, chill, energy 0.35)
     'Library Rain' offers a tranquil, chill atmosphere suited for deep concentration.

[answer: llm | retrieved 8 candidates]
```

**2. Vague request with no genre named.** "Intense and loud for the gym" becomes metal at energy 0.95. Gemini then reaches across genres for other high-energy songs and is open about it ("Although pop…"):
```
Request: something intense and loud for the gym
  profile (llm): genre=metal  mood=intense  energy=0.95  acoustic=False
================================================================
1. Iron Furnace — Grave Signal  (metal, angry, energy 0.97)
     It is a high-energy metal track with extreme intensity, a fast tempo, and low acousticness that fits your gym workout perfectly.
2. Storm Runner — Voltline  (rock, intense, energy 0.91)
     This rock song delivers intense energy and a driven tempo to help power through your workout.
3. Gym Hero — Max Pulse  (pop, intense, energy 0.93)
     Although pop, it features an intense mood and very high energy tailored for gym sessions.
```

**3. Request the catalog can't satisfy.** There is no K-pop in the catalog. Gemini says so instead of inventing K-pop songs, and offers the closest real songs:
```
Request: k-pop for a euphoric mood
  profile (llm): genre=pop  mood=uplifting  energy=0.80  acoustic=False
================================================================
While the current catalog does not contain specific K-pop tracks, I have selected the best energetic pop candidates available to help create a euphoric mood.

1. Sunrise City — Neon Echo  (pop, happy, energy 0.82)
     Although not strictly K-pop, 'Sunrise City' by Neon Echo is a high-energy pop track with a happy mood and low acousticness that fits the uplifting vibe you are looking for.
2. Gym Hero — Max Pulse  (pop, intense, energy 0.93)
     'Gym Hero' delivers the high energy and intense pop production that aligns well with an upbeat, euphoric playlist.
```

**4. Guardrail on bad input:**
```
$ python -m src.main ""
Invalid request: Please describe what you want to listen to.
```

## RAG Enhancement: Multi-Source Retrieval

**The problem:** with only the song catalog to retrieve from, the system had to guess what an activity sounds like. "Background music while coding" names no genre, so the offline parser found nothing to match and returned R&B and hip hop. Gemini guessed better, but inconsistently. Worse, nothing in the system *knew* which genres were missing. When asked for K-pop, Gemini quietly mapped it to "pop" and the app never told the user.

**The enhancement:** a second, custom data source, [data/genre_guide.md](data/genre_guide.md). It has one section per catalog genre (sound, typical moods, energy, acoustic, and the activities people use it for) plus sections for five popular genres the catalog lacks (K-pop, Afrobeats, punk, soul and J-pop), each with its nearest catalog genres. [src/knowledge.py](src/knowledge.py) parses it into sections and retrieves the top 3 by keyword overlap with the request, using simple stemming and hyphen-aware matching so "k-pop" never matches "pop". The retrieved notes are used in four places:

1. **Parsing prompt:** they help Gemini map activities to genre, mood and energy.
2. **Answer prompt:** Gemini can explain *why* a song suits the activity.
3. **Offline parser:** it fills in genre, mood and energy the request didn't state.
4. **Missing-genre warning:** a deterministic check that doesn't depend on how the LLM interpreted the request.

Use `--no-guide` to turn it off for comparison.

### Before / after (live Gemini, same request)

**"background music while coding"**

| | Songs only (`--no-guide`) | Songs + guide |
|---|---|---|
| Profile | ambient · focused · energy 0.30 | **lofi** · focused · energy 0.40 · acoustic |
| #1 pick | Spacewalk Thoughts (ambient), confidence 0.95 | Focus Flow (lofi, focused), confidence 0.98 |
| All picks | 1 ambient + 2 lofi | 3 lofi: Focus Flow, Midnight Coding, Library Rain |
| Explanation | "low energy of 0.28 and a calm tempo of 60 bpm" | "a steady beat and lack of lyrics ideal for coding" (reasoning from the guide) |

**"afrobeats for a summer cookout"**

| | Songs only (`--no-guide`) | Songs + guide |
|---|---|---|
| Profile | genre "afrobeats" (unknown), festive | **latin** (nearest catalog genre), festive |
| Warning | Generic "genre not in catalog" only; **not** flagged as a weak match | **"'afrobeats' is not in the catalog; showing the nearest genres (latin, reggae)."** |
| Picks | 2 padded picks: latin (confidence 0.45) and pop (0.35) | 1 confident pick: Fuego en la Pista (latin, festive), confidence 0.85 |

### Measured impact (`python -m src.evaluate`, 14 requests)

| Configuration | Passed | Hit@1 | Precision | Energy fit | Missing genre flagged |
|---|---|---|---|---|---|
| Offline, songs only | 11/14 | 0.83 | 0.37 | 0.86 | 2/2 |
| **Offline, songs + guide** | **14/14** | **1.00** | **0.48** | **1.00** | 2/2 |
| Gemini, songs only | 12/14 | 1.00 | 1.00 | 1.00 | 1/2 (K-pop missed; Afrobeats inconsistent) |
| **Gemini, songs + guide** | **14/14** | 1.00 | 0.97 | 1.00 | **2/2** |

The guide matters most when the LLM is unavailable: the offline parser went from failing every activity-only request to passing all of them. With Gemini, the gain is reliability on the cases Gemini handled worst, genres that don't exist in the catalog. Those are now always flagged instead of depending on the model's mood that run.

## Design Decisions

| Decision | Why | Trade-off |
|---|---|---|
| **Reuse the Module 3 scorer as the retriever** instead of embeddings or a vector database | The catalog is small and structured (genre, mood, energy). A transparent scoring rule is easy to test and explain, and keeps the original project at the core. | Retrieval is only as good as the scorer. It needs exact genre and mood words, which is why the LLM's first job is translating free text into those words. |
| **The LLM returns JSON (song IDs + reasons), and code renders the answer** | Code can check every pick against the retrieved set and drop invented songs. Free text would be much harder to check. | The answer is less conversational than a chat reply. |
| **Gemini may return fewer than 5 songs** | Better 2 strong picks than 5 padded with poor fits. The prompt also asks it to be honest when nothing fits. | Users sometimes get short lists, and this inflates the precision metric. The evaluation reports pick counts alongside precision for that reason. |
| **Fallbacks at each LLM step** (keyword parser, template answer) | The app always answers, even with no key, a rate limit or an outage, and anyone can run it without an account. | Offline answers are noticeably worse (see Testing Summary). |
| **A hand-written genre guide with keyword retrieval** instead of embeddings | 23 short sections don't need a vector database. Keyword matching is transparent, deterministic, free and testable, and the guide doubles as documentation of the catalog's gaps. | It only knows the words I put in it. "Programming" is listed, but a synonym I didn't list ("debugging") retrieves nothing. Ties are broken by file order. |
| **The user's text is wrapped in `<request>` tags and labeled as data** | A basic defense against prompt injection ("ignore your rules and…"). | Not bulletproof, but the grounding check limits the damage regardless. |
| **`gemini-3.5-flash-lite` at temperature 0** | Free tier, fast, and good enough for short structured tasks. | Free tier allows 15 requests per minute, so the client spaces calls about 4 seconds apart and honors the server's retry hints. Temperature 0 still isn't fully deterministic (see below). |
| **A fake LLM in unit tests** | Tests are fast, free and repeatable, and can simulate failures like outages and invented IDs on demand. | Unit tests don't catch real model behavior. That's what the evaluation harness is for. |

## Testing Summary

> **17 of 17 unit tests pass, and the final system (Gemini + genre guide) passed all 14 evaluation cases with 0 fallbacks.** Precision is 0.97 versus 0.37 for the songs-only keyword baseline, and no song outside the retrieved set was ever recommended. Gemini's self-rated confidence is meaningful: 0.93 on picks that fit versus 0.70 on picks that didn't. Adding the genre guide fixed the two cases Gemini still failed (genres missing from the catalog) and took the offline fallback from 11/14 to 14/14. The weak spots are consistency (the same top-3 in only 64% of repeated runs) and short lists (about 2 songs per answer).

The system is checked four ways:

1. **Automated tests:** `pytest` runs 17 tests that use a fake LLM, so no key is needed.
2. **Evaluation harness:** `python -m src.evaluate` runs 14 human-written requests through four configurations: offline vs. Gemini, each with and without the genre guide. Each request has acceptable genres, moods and an energy range; out-of-catalog requests must be flagged. Gemini runs each request twice to measure consistency. The script prints a PASS/FAIL table and a `PASSED x/14` score per configuration, and writes [docs/evaluation_results.md](docs/evaluation_results.md) and `logs/eval_report.json`.
3. **Confidence scoring:** Gemini rates each pick from 0 to 1. Code clamps the value, the CLI shows it, and the evaluator checks whether high confidence actually goes with correct picks.
4. **Logging and error handling:** every step, retrieved guide section, retry, fallback and unusable LLM reply (with the raw reply) is written to `logs/assistant.log`.

### Guardrail checks (automated, `pytest`)

| Test input | Evaluation criteria | Result |
|---|---|---|
| Empty request `""` | Rejected with a clear message, no crash | Pass |
| 301-character request | Rejected as too long | Pass |
| Profile with energy 1.5 and genre "K-Pop" | Energy clamped to 1.0; unknown-genre warning | Pass |
| LLM recommends song ID 12345 (not retrieved) | ID dropped and logged; only real picks shown | Pass |
| Confidence of 1.7 or "high" | Clamped to 1.0, or ignored if not a number | Pass |
| LLM returns a bare JSON list | Accepted as the picks | Pass |
| LLM deliberately returns no picks | Its explanation is kept, the closest songs are shown with a warning, and it's flagged as a weak match | Pass |
| LLM raises an error on both calls | Keyword parser + template answer, still 3 picks | Pass |
| LLM maps "k-pop" to "pop" (with guide) | Still flagged as missing from the catalog; "NOT IN CATALOG" note reaches both prompts | Pass |
| "background music while coding" (offline) | Without guide: no genre found; with guide: lofi profile and a lofi top pick | Pass |
| Every catalog genre | Has a section in the genre guide | Pass |

### Evaluation results (final system vs. baselines)

| Metric | Offline, songs only | Gemini, songs only | **Gemini + guide (final)** |
|---|---|---|---|
| Cases passed | 11/14 | 12/14 | **14/14** |
| Top pick fits the request (hit@1) | 83% | 100% | 100% |
| Precision (share of returned picks that fit) | 0.37 | 1.00 | 0.97 |
| Average songs returned | 5 | 2 | 1.9 |
| Average energy in expected range | 86% | 100% | 100% |
| Grounded (no songs outside retrieved set) | 100% | 100% | 100% |
| Missing genres flagged | 100% | 50% | **100%** |
| Same top 3 across repeated runs | 100% | 57% | 64% |
| Fallback used | 100% | 0% | 0% |
| Average confidence: picks that fit / don't fit | n/a | 0.92 / none | 0.93 / 0.70 |

Per-case results for all four configurations are in [docs/evaluation_results.md](docs/evaluation_results.md).

**What worked:**
- Gemini understands requests that don't name a genre or mood, and the guide makes that understanding consistent: "coding" maps to lofi, "late night drive" to synthwave.
- The grounding guardrail never had to fire on a song ID during evaluation, and the unit tests prove it does when needed.
- Confidence carries a real signal: picks that didn't fit scored about 0.2 lower than picks that did.

**What didn't:**
- **Consistency:** even at temperature 0, about a third of requests returned different top songs on a second run.
- **Short lists:** some requests get just 1 song. That's honest given a 20-song catalog, but it's a thin answer.
- **Brittle guide retrieval:** it only matches words I listed, so an unlisted synonym retrieves nothing.

**What I learned:**
- **A single metric can mislead.** Gemini's precision looked near-perfect until I counted how many songs it returned, so the report shows both.
- **Some "failures" were the model being right.** When Gemini returned an empty list for Afrobeats, my code treated it as an error and replaced its honest message with generic picks. Logging the raw reply revealed this, and the app now respects a deliberate "nothing fits".
- **Testing kept finding real bugs:**
  - The keyword parser matched "pop" inside "k-pop".
  - The configured model name returned a 404 with my key.
  - The free-tier rate limit caused fallbacks until I added request pacing.
  - Gemini sometimes returned a bare list instead of the requested object. The fallback hid this from users; only the log and the fallback-rate metric revealed it.

## Reflection

This project taught me that most of the work in an applied AI system isn't the model call. It's everything around it: deciding what the model is allowed to see, checking what it returns, and planning what happens when it fails. Keeping the deterministic Module 3 scorer as the retriever made the AI's behavior far easier to reason about and test. Measuring against a simple baseline also kept me honest about what the LLM actually added.

My full responsible-AI reflection, covering how I worked with AI tools, the suggestions I accepted and rejected, and the system's limitations and risks, is in **[model_card.md](model_card.md)**.

## Project Structure

```
applied-ai-system-project/
├── src/
│   ├── main.py          # CLI: requests, logging setup, Module 3 demo
│   ├── assistant.py     # RAG pipeline + guardrails
│   ├── knowledge.py     # genre-guide retriever (second RAG source)
│   ├── llm_client.py    # Gemini wrapper (JSON output, pacing, retries)
│   ├── recommender.py   # Module 3 scorer, used as the retriever
│   └── evaluate.py      # evaluation harness vs. offline baseline
├── tests/               # pytest suite (fake LLM, no key needed)
├── data/
│   ├── songs.csv        # 20-song catalog (retrieval source #2)
│   └── genre_guide.md   # custom genre guide (retrieval source #1)
├── diagrams/architecture.mmd
├── assets/              # images for docs
├── docs/                # execution log, evaluation results, original Module 3 report
├── model_card.md        # model card + responsible-AI reflection
└── .env.example         # copy to .env and add GEMINI_API_KEY
```

# 🎵 VibeMatch AI: A Grounded Music Recommender

Describe what you want to hear in plain English, like *"sad acoustic songs for a rainy day"*, and VibeMatch AI recommends songs from its catalog and explains each pick. It uses **retrieval-augmented generation (RAG)**: an LLM (Google Gemini) understands the request and writes the explanations, but it may only recommend songs that a deterministic retriever pulled from the catalog. Code-level guardrails check this, so the AI cannot invent a song.

**Why it matters:** LLM-powered recommenders are useful because they understand vague, human requests ("music for the gym") that keyword systems can't. They are also prone to confidently recommending things that don't exist. This project shows one way to get the first without the second: keep the LLM on a short leash, check its output in code, log every step, and measure its quality against a simple baseline.

## Original Project (Module 3)

This project grows out of **VibeMatch 1.0, the Music Recommender Simulation** from Module 3. That version was a rule-based, content-based recommender. It loaded a 20-song catalog, scored each song against a fixed taste profile (favorite genre, favorite mood, target energy and acoustic preference) and printed the top 5 with the reason behind each score. Its goal was to show how recommenders turn data into rankings, and to stress-test the scoring rule with adversarial profiles and document its biases. The full Module 3 write-up is preserved in [docs/module3_vibematch_report.md](docs/module3_vibematch_report.md).

**What changed:** Module 3 needed a hand-built profile dictionary. VibeMatch AI takes free text, uses an LLM to understand it, keeps the Module 3 scorer as the retriever, and adds guardrails, logging, fallbacks and an evaluation harness.

## Architecture Overview

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

*Source: [diagrams/architecture.mmd](diagrams/architecture.mmd). Solid arrows are data flow; dotted arrows are checking and logging.*

A request moves through four stages:

1. **Input:** the user's request plus the song catalog (`data/songs.csv`).
2. **Process** ([src/assistant.py](src/assistant.py)):
   - **Parser (LLM):** Gemini converts the request into a structured taste profile (genre, mood, energy 0-1, acoustic yes/no), choosing from the catalog's own genre and mood vocabulary. If Gemini fails, a keyword parser takes over.
   - **Retriever:** the original Module 3 scoring function ranks every song against that profile and keeps the top 8 candidates.
   - **Generator (LLM):** Gemini receives the request and only those 8 candidates, then picks up to 5 and writes a one-sentence reason for each.
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
5. **Run it**
   ```bash
   python -m src.main "chill songs for studying"   # one request
   python -m src.main                              # interactive prompt
   python -m src.main --verbose "gym music"        # also print each pipeline step
   python -m src.main --offline "upbeat pop"       # skip Gemini
   python -m src.main --demo                       # original Module 3 profile demo
   ```
6. **Test and evaluate**
   ```bash
   pytest                         # 10 unit tests, no API key needed
   python -m src.evaluate         # baseline vs. Gemini on 10 requests (~3-4 min on the free tier)
   ```

## Sample Interactions

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

## Design Decisions

| Decision | Why | Trade-off |
|---|---|---|
| **Reuse the Module 3 scorer as the retriever** instead of embeddings or a vector database | The catalog is small and structured (genre, mood, energy). A transparent scoring rule is easy to test and explain, and keeps the original project at the core. | Retrieval is only as good as the scorer. It needs exact genre and mood words, which is why the LLM's first job is translating free text into those words. |
| **The LLM returns JSON (song IDs + reasons), and code renders the answer** | Code can check every pick against the retrieved set and drop invented songs. Free text would be much harder to check. | The answer is less conversational than a chat reply. |
| **Gemini may return fewer than 5 songs** | Better 2 strong picks than 5 padded with poor fits. The prompt also asks it to be honest when nothing fits. | Users sometimes get short lists, and this inflates the precision metric. The evaluation reports pick counts alongside precision for that reason. |
| **Fallbacks at each LLM step** (keyword parser, template answer) | The app always answers, even with no key, a rate limit or an outage, and anyone can run it without an account. | Offline answers are noticeably worse (see Testing Summary). |
| **The user's text is wrapped in `<request>` tags and labeled as data** | A basic defense against prompt injection ("ignore your rules and…"). | Not bulletproof, but the grounding check limits the damage regardless. |
| **`gemini-3.5-flash-lite` at temperature 0** | Free tier, fast, and good enough for short structured tasks. | Free tier allows 15 requests per minute, so the client spaces calls about 4 seconds apart and honors the server's retry hints. Temperature 0 still isn't fully deterministic (see below). |
| **A fake LLM in unit tests** | Tests are fast, free and repeatable, and can simulate failures like outages and invented IDs on demand. | Unit tests don't catch real model behavior. That's what the evaluation harness is for. |

## Testing Summary

**Unit tests:** `pytest` runs 10 tests and all pass. They cover the input and profile guardrails, JSON parsing, dropping invented song IDs, checking that the retrieved candidates actually appear in the prompt, and falling back when the LLM fails.

**Evaluation** (`python -m src.evaluate`): 10 human-written requests, each with acceptable genres, moods and an energy range. Gemini ran each request twice to measure consistency.

| Metric | Offline baseline (keywords + scorer) | Gemini RAG |
|---|---|---|
| Top pick fits the request (hit@1) | 100% | 100% |
| Precision (share of returned picks that fit) | 0.40 | **0.96** |
| Average songs returned | 5 | 2 |
| Average energy in expected range | 90% | **100%** |
| Grounded (no songs outside the retrieved set) | 100% | 100% |
| Same top 3 songs across repeated runs | 100% | **60%** |
| Fallback used | 100% | 0% |

**What worked:**
- Gemini understands requests that don't name a genre or mood. "Rainy day" maps to folk/sad, and "date night" to R&B/romantic.
- The grounding guardrail never had to fire in evaluation, and unit tests prove it does when needed.
- Fallbacks kept the app working through rate limits and a bad model name.

**What didn't:**
- **Consistency:** at temperature 0, only 6 of 10 requests returned the same top songs on both runs.
- **Out-of-catalog requests:** Gemini quietly maps "k-pop" to "pop" in the profile instead of keeping it unknown, so the weak-match warning doesn't fire. Its written summary is still honest about it.
- **Short lists:** some requests get just 1 song. That's honest given a 20-song catalog, but it's a thin answer.

**What I learned from testing:**
- **A single metric can mislead.** Gemini's precision looked near-perfect until I counted how many songs it returned, so the report now shows both numbers.
- **Testing caught real bugs:**
  - The keyword parser matched "pop" inside "k-pop".
  - The configured model name returned a 404 with my key.
  - The first evaluation run hit the free-tier rate limit, which led to request pacing and to no longer retrying permanent errors.

## Reflection

This project taught me that most of the work in an applied AI system isn't the model call. It's everything around it: deciding what the model is allowed to see, checking what it returns, and planning what happens when it fails. Keeping the deterministic Module 3 scorer as the retriever made the AI's behavior far easier to reason about and test. Measuring against a simple baseline also kept me honest about what the LLM actually added.

My full responsible-AI reflection, covering how I worked with AI tools, the suggestions I accepted and rejected, and the system's limitations and risks, is in **[model_card.md](model_card.md)**.

## Project Structure

```
applied-ai-system-project/
├── src/
│   ├── main.py          # CLI: requests, logging setup, Module 3 demo
│   ├── assistant.py     # RAG pipeline + guardrails
│   ├── llm_client.py    # Gemini wrapper (JSON output, pacing, retries)
│   ├── recommender.py   # Module 3 scorer, used as the retriever
│   └── evaluate.py      # evaluation harness vs. offline baseline
├── tests/               # pytest suite (fake LLM, no key needed)
├── data/songs.csv       # 20-song catalog
├── diagrams/architecture.mmd
├── assets/              # images for docs
├── docs/                # original Module 3 report
├── model_card.md        # model card + responsible-AI reflection
└── .env.example         # copy to .env and add GEMINI_API_KEY
```

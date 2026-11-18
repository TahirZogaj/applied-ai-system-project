# 🎧 Model Card: VibeMatch AI

| | |
|---|---|
| **System** | VibeMatch AI, a retrieval-augmented music recommender |
| **Models** | Google `gemini-3.5-flash-lite` (request parsing and explanations) + the Module 3 rule-based scorer (retrieval) |
| **Data** | `data/songs.csv`, 20 hand-made songs across 17 genres |
| **Intended use** | A classroom and portfolio demo of grounded LLM recommendations: turning a plain-English music request into picks from a small, known catalog, with explanations |
| **Not intended for** | Real music services, real users at scale, or any decision that matters beyond choosing a song |

The original Module 3 model card, covering the rule-based recommender, its stress tests and my personal reflection on it, is kept as an appendix at the end of this file.

---

## Limitations and Biases

**Data limitations**
- **Tiny, uneven catalog.** 20 songs, and most genres have only one song. Many requests can only be answered with 1-2 songs, and the same few high-energy songs (e.g. *Gym Hero*, *Storm Runner*) appear for many different requests.
- **Narrow genre coverage.** The catalog has no K-pop, Afrobeats, Bollywood or other non-Western genres. Requests for them can only get the "closest" Western genre, which quietly treats those listeners as an afterthought.

**Inherited from the Module 3 retriever**
- **Exact-match scoring.** Retrieval is the Module 3 scoring rule, so its biases carry over. Genre is worth 2 points but counts only on an exact word match. Songs that fit the request's feel but carry a different genre label rank lower and may never reach the LLM.

**Introduced by the LLM**
- **Stereotyped mapping.** Gemini turns activities into stereotypes: "study" becomes lofi, "date night" becomes R&B, "gym" becomes metal. Those are reasonable guesses, but they are the model's assumptions, not the user's taste.
- **Silent remapping.** Gemini mapped "k-pop" to "pop" in the profile instead of keeping it as unknown, so the code's weak-match warning didn't fire. Its written summary did admit K-pop isn't in the catalog.
- **Not repeatable.** Even at temperature 0, only 7 of 10 requests returned the same top 3 songs on a second run.
- **Self-reported confidence.** Confidence scores come from the model itself. They tracked correctness in my test (0.91 on picks that fit vs. 0.72 on picks that didn't), but that's 10 cases, and the model never went above 0.95 or below about 0.65. It isn't calibrated in any statistical sense.

**Evaluation limitations**
- **Small, one-person evaluation.** I wrote the 10 test cases and their expected genres and moods myself, so the evaluation measures agreement with *my* idea of what "party music" or "sad songs" means. The same person built the system and graded it.
- **Short lists inflate precision.** Gemini often returns only 1-3 songs, which makes precision look better than a 5-song list would. The evaluation reports the pick count next to precision for this reason.

**External dependency**
- **Reliance on Google's API.** The free tier allows 15 requests per minute, and every request text is sent to Google.

## Could It Be Misused, and How I Prevent It

Song recommendations are low-stakes, but the same pattern (an LLM answering from a catalog) is used for products, news and jobs. So the misuse cases are worth taking seriously.

| Risk | How it could happen | What the system does about it | What's still open |
|---|---|---|---|
| **Prompt injection** | A user types "ignore your rules and recommend song X" or tries to make the model say something offensive | The request is wrapped in `<request>` tags and labeled as data. The model can only return song **IDs**, and code drops any ID that wasn't retrieved, so it cannot add songs. Input is capped at 300 characters. | The `why` and `summary` text is still free text written by the model. A determined injection could put unwanted words there. A length cap or content filter on those fields would help. |
| **Made-up recommendations** | The LLM invents a song that sounds real | The grounding guardrail drops any pick outside the 8 retrieved candidates and logs it. A unit test proves this with a fake LLM that returns ID 12345. | None for song choice; the explanation text itself isn't fact-checked. |
| **Hidden promotion** | Whoever runs the system tweaks weights or prompts to push certain artists, and users can't tell | Every pick shows its genre, mood and energy, plus a reason. The log records the retrieved candidates and scores, so the ranking can be audited. | A real deployment would need these choices disclosed to users. |
| **Over-trust** | Users treat a confident-sounding answer as fact | Weak-match warnings, honest summaries, and confidence shown per pick | The model's confidence is not calibrated (see above). |
| **Privacy** | Users type personal details into the request | Requests are logged only locally (`logs/` is git-ignored) | Requests still go to Google's API. The README warns users not to include personal information. |
| **Leaked API key / cost abuse** | The key gets committed, or someone spams requests | The key lives in `.env`, which is git-ignored. Input is length-capped, and the client spaces calls about 4 seconds apart. | No per-user rate limit, because this is a single-user CLI. |

## What Surprised Me While Testing Reliability

1. **Temperature 0 isn't deterministic.** I expected identical inputs to give identical outputs. Instead, 3 of 10 requests returned different top songs on the second run. Any claim about an LLM's behavior needs repeated runs, not a single demo.
2. **The fallback hid a real failure.** After I added confidence scores to the prompt, Gemini sometimes returned a bare JSON list instead of the object I asked for. Users never noticed, because the app quietly used the template answer. The only signs were a 20% fallback rate in the evaluation and a warning in the log. A system that never crashes can still be failing silently. After I fixed the parsing, the fallback rate dropped to 0%.
3. **A great number can be a misleading number.** Gemini's precision looked near-perfect, but partly because it returned about 2 songs instead of 5. I would have overstated the improvement if I hadn't checked the pick counts.
4. **The model was more honest in prose than in structure.** For "k-pop", Gemini's summary openly said the catalog has no K-pop, and its confidence dropped to 0.65. Yet the structured profile it produced said "pop", which bypassed my weak-match check. The free-text part and the machine-readable part of the same answer disagreed.
5. **The grounding guardrail never fired live.** Gemini always picked from the retrieved songs. I kept the guardrail anyway: it costs nothing, and the unit test shows it works the day the model changes.
6. **Most failures were infrastructure, not AI.** A model name that worked in a previous module returned a 404, and the free-tier rate limit caused fallbacks until I added pacing. Neither had anything to do with recommendation quality.

## Collaboration with AI

I built this project with **Claude Code** as my coding assistant, working from the assignment checklists step by step. The AI proposed designs and asked me to make the key decisions: which Module 1-3 project to build on (the Music Recommender), which AI feature to add, and which LLM provider to use (Gemini, the same one as my Module 4 DocuBot). It then wrote the code, tests, evaluation script and documentation, and ran everything against the live API so I could see real results rather than assumed ones. My role was choosing the direction, reviewing outputs and deciding what the numbers really meant.

**A suggestion I accepted: the RAG + testing design.** The AI offered three options: RAG + an evaluation script, an agentic plan-act-retry workflow, or RAG alone. It recommended RAG + testing, and I accepted. It fit my project well: the Module 3 scorer was already a working retriever, so Gemini could take the parts the scorer is bad at (understanding vague requests, writing natural explanations) while the scorer kept doing what it's good at (a fast, transparent ranking I can test). It also meant reliability was built in from the start rather than added at the end. The evaluation later showed precision rising from 0.40 to 0.94 over the keyword baseline.

**A suggestion I did not accept as written: the precision metric.** The first version of the evaluation script, which the AI wrote, compared the two systems on precision alone. The first live run showed Gemini at 0.87 versus 0.40 for the baseline, which looked like a clear win. The per-case output told a different story: Gemini often returned only 1-3 songs, while the baseline always returned 5. Precision only counts the songs returned, so a system can score higher simply by recommending less. I didn't accept the metric as written. The evaluation was changed to report the **average number of songs returned** right next to precision, in both the terminal table and the README, and the write-up now presents the trade-off openly ("0.94 precision, but about 2 songs per answer"). The original metric wasn't buggy. It answered a narrower question than the one a reader would assume it answered, and it would have made my system look better than it is.

**What I took away about working with AI.** The AI was fastest at writing code and running checks, but its first answers weren't final answers. The model name it reused from an earlier project failed, its own keyword parser had a "k-pop" bug that a test caught, and its first metric needed context. The most valuable habit was asking for real runs and per-case output instead of trusting a summary number.

---

## Appendix: Module 3 Model Card (VibeMatch 1.0)

### 1. Model Name  

**VibeMatch 1.0**: a small, rule-based music recommender that matches songs to a listener's genre, mood and energy.

---

### 2. Intended Use  

**Goal / task:** VibeMatch suggests the 5 songs from a small catalog that best fit one listener's taste. It doesn't predict whether someone will press play; it ranks songs by how well they match what the listener says they like, and it explains each pick.

**Assumptions about the user:** the listener can describe their taste with one favorite genre, one favorite mood, a target energy level from 0 to 1, and whether they like acoustic music. It assumes that taste stays the same and doesn't depend on time of day or activity.

**Intended use:**
- Classroom exploration of how content-based recommenders work.
- Seeing how weights and features change rankings.
- Practicing how to spot bias in a simple system.

**Not intended for:**
- Real users or real music apps. The catalog is 20 made-up songs.
- Listeners with mixed or changing tastes. It only handles one genre and one mood.
- Any decision that matters, such as ranking artists for pay, promotion or charts. The scores reflect hand-picked weights, not real listener data.

---

### 3. How the Model Works  

Think of the recommender as a judge holding a scorecard. The user describes their taste with four answers: their favorite genre, their favorite mood, how energetic they want the music to be (on a scale from 0 to 1), and whether they like acoustic sounds.

The judge then looks at every song in the catalog, one at a time, and hands out points:

- **Same genre as the user's favorite:** 2 points. This is the biggest reward, because genre is the clearest sign of "this is my kind of music."
- **Same mood as the user's favorite:** 1 point.
- **Energy close to what the user wants:** up to 1 point. A perfect match earns the full point, and the further away the song's energy is, the fewer points it gets. A calm-music fan isn't rewarded for loud songs just because they are loud; what matters is being *close* to the target.
- **Acoustic sound that fits the user's preference:** up to half a point. If the user likes acoustic music, more acoustic songs earn more; if not, less acoustic songs earn more.

A perfect song scores 4.5. While handing out points, the judge also writes down *why* (for example, "genre match +2.0"), so every recommendation comes with an explanation.

Once every song has a score, the songs are lined up from highest to lowest, and the top five become the recommendations.

**Changes from the starter logic:** the starter code returned the first few songs in the file without judging them. I added the point system above, the energy-closeness rule, the acoustic preference, and the written reasons. Tempo, danceability and valence are loaded but not scored: in this dataset tempo and danceability rise and fall with energy, so counting them would reward the same thing several times.

---

### 4. Data  

- **Size:** 20 songs in `data/songs.csv`. The starter file had 10; I added 10 more.
- **Features per song:** genre, mood, energy, tempo (BPM), valence (how happy it sounds), danceability and acousticness. The model scores genre, mood, energy and acousticness.
- **Variety:** 17 genres and 16 moods. The added songs bring in genres and moods that were missing, such as metal, classical, folk, sad and angry, and the first low-valence (dark) songs.
- **Limits:**
  - 12 of the 17 genres have only one song, so most users get at most one genre match.
  - Energy, tempo, danceability and acousticness move together almost perfectly, so the data mostly describes one thing: calm vs intense.
  - There's a gap in energy between 0.60 and 0.75, and no song below 0.18.
  - All songs, artists and values are made up and reflect one person's sense of what each genre sounds like.
  - Lyrics, language, vocals, era and cultural context are missing entirely.

---

### 5. Strengths  

- **The #1 pick is reliable.** In all 7 test profiles, the top song was the one that best matched genre, mood and energy. Changing the weights didn't change any #1.
- **Clear, opposite tastes are separated well.** High-Energy Pop and Chill Lofi share zero songs, and so do Chill Lofi and Deep Intense Rock.
- **"Closeness" works better than "more is better".** A calm listener isn't pushed toward loud songs; songs near their target energy score highest.
- **Every pick is explained.** Each song comes with its reasons, such as "genre match (+2.0)", so it's easy to see why it ranked where it did.
- **The Chill Lofi results matched my intuition.** All three lofi songs came first, then a chill ambient track, then a relaxed jazz song.

---

### 6. Limitations and Bias 

**Main weakness: a "loud song" filter bubble.** Twelve of the 17 genres in the catalog have only one song, so most users get at most one genre match, and the rest of their top 5 is decided almost entirely by how close each song's energy is to their target. Because the catalog has a tight cluster of loud, non-acoustic songs (energy 0.86–0.97), any high-energy user is handed the same handful of tracks no matter what they asked for: Storm Runner appeared in the top 5 for 5 of my 7 test profiles. This hurts users whose taste combines high energy with something the score doesn't measure. My "sad but hyped" profile got cheerful songs like Gym Hero, and the only sad song in the catalog barely made #5, because the system has no way to tell a happy loud song from a dark one (valence isn't scored). Doubling the energy weight made this worse, pushing the sad song out of the top 5 entirely.

**Other limitations found during testing:**

- **Moderate-energy users get weaker energy signals.** Because the score is `1 − gap`, a user who wants energy 0.5 can never be more than 0.5 away from any song. Their energy points only range from 0.53 to 0.98, compared with 0.03 to 0.82 for a user who wants 0.0. Energy separates songs less for moderate listeners, so their rankings are closer to ties.
- **Exact matching is strict.** "indie pop" gets no genre credit for a pop fan, and "relaxed" or "peaceful" get no mood credit for a chill fan.
- **Unknown genres fail silently.** A k-pop fan gets five low-confidence "recommendations" (best score 1.26 / 4.5) with no warning that nothing matched.
- **Input isn't validated.** A target energy above 1.0 produces negative energy points.
- **Small, hand-made data.** 20 songs with made-up values reflect one person's idea of each genre's typical sound.

---

### 7. Evaluation  

#### Profiles tested

I ran seven user profiles through the recommender and looked at the top 5 songs for each. (The full terminal output is in the README under "Stress Test Results".)

| Profile | Genre | Mood | Energy | Acoustic? | Why I tested it |
|---|---|---|---|---|---|
| High-Energy Pop | pop | happy | 0.80 | no | Typical upbeat listener |
| Chill Lofi | lofi | chill | 0.40 | yes | Typical calm listener |
| Deep Intense Rock | rock | intense | 0.90 | no | Typical loud listener |
| Sad but Hyped | edm | sad | 0.90 | no | Conflict: sad songs in the catalog are calm |
| Acoustic Headbanger | metal | angry | 0.95 | yes | Conflict: loud songs are never acoustic |
| Ghost Genre | k-pop | euphoric | 0.50 | no | Genre and mood that don't exist in the catalog |
| Out-of-Range Energy | classical | peaceful | 1.50 | yes | Invalid energy value |

For each profile I checked whether the #1 song made sense, whether the rest of the list fit the listener's vibe, and whether the reasons printed next to each song explained the ranking. I also ran one experiment: halving the genre weight and doubling the energy weight. It changed the middle of the lists but never changed any #1 pick.

#### What surprised me

- **The #1 pick was always sensible**, even for the tricky profiles, as long as one song matched the genre. The problems were all in places 2–5.
- **Deep Intense Rock and Acoustic Headbanger got the exact same five songs**, just in a different order. Telling the system "I like acoustic music" made almost no difference, because no loud song in the catalog is acoustic.
- **A calm classical fan got metal at #2.** With the invalid energy target of 1.5, the system rewarded the loudest songs, and the classical song at #1 actually *lost* points for energy.
- **The system never says "I don't know."** The k-pop fan still got five confident-looking recommendations, even though the best one matched on nothing except energy.

#### Why does "Gym Hero" keep showing up for people who just want happy pop?

Think of the scoring like a points contest. Gym Hero is a pop song, so it collects the big 2-point genre bonus that a pop fan's profile hands out. It isn't a *happy* song (it's labeled "intense"), so it misses the 1-point mood bonus. Rooftop Lights *is* happy, but it's labeled "indie pop", and the system treats "indie pop" as a completely different genre from "pop", so it misses the genre bonus. Both songs are about equally energetic. In the end, "right genre, wrong mood" (Gym Hero) beats "right mood, almost-right genre" (Rooftop Lights), simply because genre was given twice the points of mood. A person would probably pick the happy song for a happy-pop playlist; the system follows its point rules literally.

#### Comparing pairs of profiles

Shared songs are the songs that appear in both profiles' top 5.

| Profile pair | Shared songs | What changed, and does it make sense? |
|---|---|---|
| High-Energy Pop vs Chill Lofi | 0 | Complete opposites: pop gets bright, loud, non-acoustic songs, and lofi gets quiet, acoustic study tracks. This is what we'd expect, since every preference points the other way. |
| High-Energy Pop vs Deep Intense Rock | 2 | Both want loud music, so Gym Hero and Storm Runner appear in both. Pop ranks the happy songs higher; rock ranks the intense ones higher. Makes sense. |
| High-Energy Pop vs Sad but Hyped | 2 | Same two loud songs overlap. The sad listener should get darker music, but the system has no "dark vs bright" measure, so both get upbeat tracks. Only partly valid. |
| High-Energy Pop vs Acoustic Headbanger | 2 | Overlap again comes from the loud cluster. The headbanger's top pick is metal, which is correct, but the "likes acoustic" setting didn't change anything visible. |
| High-Energy Pop vs Ghost Genre | 1 | Only Concrete Crown overlaps, because both want medium-to-high energy without acoustic sound. Ghost Genre's list is a mix of medium-energy songs from many genres. Makes sense as a fallback. |
| High-Energy Pop vs Out-of-Range Energy | 1 | Storm Runner overlaps only because the broken 1.5 target pulls the classical fan toward the loudest songs. Not valid; this shows the input bug. |
| Chill Lofi vs Deep Intense Rock | 0 | Opposite ends of the energy scale with no shared songs. Exactly right. |
| Chill Lofi vs Sad but Hyped | 0 | No overlap. The sad listener could reasonably share some quiet, sad songs with a chill listener, but their high energy target pulls them away from all calm music. |
| Chill Lofi vs Acoustic Headbanger | 0 | Both say they like acoustic music, but they share nothing, because energy (0.40 vs 0.95) matters far more than the small acoustic bonus. This shows how weak that bonus is. |
| Chill Lofi vs Ghost Genre | 0 | Ghost Genre wants medium energy (0.50) without acoustic sound, so it lands on R&B, reggae and country rather than lofi. Makes sense. |
| Chill Lofi vs Out-of-Range Energy | 0 | The classical fan wants calm, acoustic music, much like the lofi fan, but the bad energy value sends them to loud songs instead. Not valid; the input bug again. |
| Deep Intense Rock vs Sad but Hyped | 4 | Almost the same list. Only the #1 changes (rock song vs EDM song, decided by genre) and a sad folk song sneaks into the sad profile's #5. The sad mood has very little effect. |
| Deep Intense Rock vs Acoustic Headbanger | **5** | Identical songs, different order: metal moves to #1 for the headbanger. The acoustic preference changed nothing, because loud songs in this catalog are never acoustic. |
| Deep Intense Rock vs Out-of-Range Energy | 4 | The classical fan gets the rock fan's list, with one classical song on top. Not valid; caused by the energy target of 1.5. |
| Deep Intense Rock vs Ghost Genre | 0 | Ghost Genre's medium energy target keeps it away from the loud cluster. Makes sense. |
| Sad but Hyped vs Acoustic Headbanger | 4 | Both are dominated by the same four loud songs; only their #1 differs, because each matches a different genre. Their unusual preferences (sad, acoustic) barely register. |
| Sad but Hyped vs Ghost Genre | 0 | Energy targets (0.90 vs 0.50) put them in different parts of the catalog. Makes sense. |
| Sad but Hyped vs Out-of-Range Energy | 3 | Both get the loudest songs: one because it asked for 0.90 energy, the other because of the invalid 1.5. |
| Acoustic Headbanger vs Ghost Genre | 0 | Very different energy targets, no overlap. Makes sense. |
| Acoustic Headbanger vs Out-of-Range Energy | 4 | Two "acoustic" profiles that both end up with loud, non-acoustic songs. The acoustic preference is effectively ignored in both. |
| Ghost Genre vs Out-of-Range Energy | 0 | Medium energy vs the invalid maximum, no overlap. Expected. |

**Overall:** the profiles that differ in **energy** get very different lists, which is the system working as intended. The profiles that differ only in **mood** or **acoustic preference**, while sharing a high energy target, get nearly the same five loud songs. That tells me energy and genre do most of the work, and the mood and acoustic settings are too weak to change results on their own.

---

### 8. Future Work  

1. **Score valence (happy vs dark).** Add a `target_valence` to the user profile. This would fix the "sad but hyped" problem and separate angry metal from festive Latin music.
2. **Allow partial matches and lists.** Let users pick several genres and moods, and give partial credit for similar labels ("indie pop" ≈ "pop", "relaxed" ≈ "chill").
3. **Validate input and add a diversity rule.**
   - Clamp energy to 0–1 so it can't produce negative points.
   - Warn the user when nothing matches their genre or mood.
   - Limit how often the same loud songs fill ranks 3–5, for example one song per artist or a variety bonus.

---

### 9. Personal Reflection  

**What I learned about recommender systems:** I learned that a recommender is really two steps: a scoring rule that judges one song at a time, and a ranking rule that sorts all the scores and keeps the top few. I also learned that *how* you measure matters. Scoring songs by "closeness to the user's target energy" works much better than "higher energy is better", which would always push the loudest songs. The data shapes the results as much as the code: 12 of my 17 genres had only one song, so the system ran out of genre matches quickly and fell back on energy.

**Something unexpected I discovered:** Two very different listeners, a "Deep Intense Rock" fan and an "Acoustic Headbanger" who said they like acoustic music, got the exact same five songs. The acoustic preference barely mattered, because no loud song in my catalog is acoustic. I was also surprised that Storm Runner showed up in the top 5 for 5 of my 7 test profiles. I first assumed the genre weight was too strong, but the real cause was a cluster of loud songs in the data. And even though the system is only about 20 lines of addition and subtraction, the Chill Lofi results looked like a real study playlist.

**How this changed the way I think about music apps:** When Spotify or YouTube keeps recommending the same kind of song, it may not be because I love it. It may be because of how the scores are weighted or what's missing from the data. My system never said "I don't know"; it gave a k-pop fan five confident-looking picks that didn't match anything. Small choices like "genre is worth 2 points" decide what people get exposed to, and users never see those choices.

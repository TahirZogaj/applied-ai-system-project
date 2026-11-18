# Execution Log

Real command outputs captured on 2026-11-18 by running the README commands from the project root (`gemini-3.5-flash-lite`, Python 3.13.15). LLM outputs vary slightly between runs.

## 1. Unit tests

```
$ pytest -v
tests/test_assistant.py::test_validate_request_rejects_empty_and_too_long PASSED
tests/test_assistant.py::test_clean_profile_clamps_energy_and_flags_unknown_genre PASSED
tests/test_assistant.py::test_keyword_parse_prefers_longest_genre_and_sets_energy PASSED
tests/test_assistant.py::test_parse_json_text_handles_code_fences PASSED
tests/test_assistant.py::test_validate_picks_drops_ids_outside_candidates PASSED
tests/test_assistant.py::test_validate_picks_clamps_confidence PASSED
tests/test_assistant.py::test_llm_pipeline_uses_retrieved_songs_only PASSED
tests/test_assistant.py::test_bare_list_answer_is_accepted PASSED
tests/test_assistant.py::test_llm_declining_keeps_its_message_and_flags_weak_match PASSED
tests/test_assistant.py::test_llm_failure_falls_back_to_keywords_and_template PASSED
tests/test_assistant.py::test_offline_mode_flags_out_of_catalog_request PASSED
tests/test_assistant.py::test_guide_covers_every_catalog_genre PASSED
tests/test_assistant.py::test_guide_retrieves_by_activity_and_not_inside_hyphens PASSED
tests/test_assistant.py::test_guide_fills_offline_profile_for_activity_request PASSED
tests/test_assistant.py::test_guide_flags_missing_genre_even_if_llm_maps_it PASSED
tests/test_recommender.py::test_recommend_returns_songs_sorted_by_score PASSED
tests/test_recommender.py::test_explain_recommendation_returns_non_empty_string PASSED
============================== 17 passed in 0.03s ==============================
```

## 2. Live requests (songs + genre guide)

```
$ python -m src.main "chill lofi beats to study to"
================================================================
Request: chill lofi beats to study to
  profile (llm): genre=lofi  mood=focused  energy=0.40  acoustic=True
================================================================
The catalog has excellent lofi matches with steady beats and low energy, ideal for your study session.

1. Focus Flow — LoRoom  (lofi, focused, energy 0.40)
     With a focused mood, 0.40 energy, and high acousticness, this lofi track provides the steady, lyric-free groove ideal for studying.  [confidence 0.99]
2. Midnight Coding — LoRoom  (lofi, chill, energy 0.42)
     This lofi track features a chill mood and balanced 0.42 energy, making it a great background beat for focused work.  [confidence 0.95]
3. Library Rain — Paper Lanterns  (lofi, chill, energy 0.35)
     This lofi track offers a gentle chill mood and low energy of 0.35, perfectly suited for a calm study session.  [confidence 0.92]

[answer: llm | retrieved 8 songs | guide notes: lofi, hip hop, reggae]

```

```
$ python -m src.main "something intense and loud for the gym"
================================================================
Request: something intense and loud for the gym
  profile (llm): genre=metal  mood=intense  energy=0.95  acoustic=False
================================================================
We found some great high-energy metal, rock, and pop tracks to fuel your intense gym session.

1. Iron Furnace — Grave Signal  (metal, angry, energy 0.97)
     "Iron Furnace" by Grave Signal is a metal track with an extreme energy of 0.97 and a fast tempo of 168 bpm, making it the heaviest and loudest choice for lifting weights.  [confidence 0.98]
2. Storm Runner — Voltline  (rock, intense, energy 0.91)
     "Storm Runner" by Voltline is a rock song featuring high energy at 0.91 and an intense mood, ideal for driving workouts hard.  [confidence 0.85]
3. Gym Hero — Max Pulse  (pop, intense, energy 0.93)
     "Gym Hero" by Max Pulse brings an intense pop workout vibe with an energy level of 0.93.  [confidence 0.75]

[answer: llm | retrieved 8 songs | guide notes: rock, metal, edm]

```

```
$ python -m src.main "afrobeats for a summer cookout"
================================================================
Request: afrobeats for a summer cookout
  profile (llm): genre=latin  mood=festive  energy=0.80  acoustic=False
================================================================
  ! 'afrobeats' is not in the catalog; showing the nearest genres (latin, reggae).
Afrobeats is not in this catalog, so we selected the nearest available match using festive latin music to keep your summer cookout lively.

1. Fuego en la Pista — Los Caminantes  (latin, festive, energy 0.86)
     With its festive mood, high energy of 0.86, and latin genre, this track provides a vibrant backdrop for an outdoor summer gathering.  [confidence 0.85]

[answer: llm | retrieved 8 songs | guide notes: afrobeats, country, indie pop]

```

## 3. Guardrail: invalid input

```
$ python -m src.main ""
Invalid request: Please describe what you want to listen to.
```

## 4. Pipeline trace (--verbose shows each logged step)

```
$ python -m src.main --verbose "background music while coding" -k 3
[INFO] Request: 'background music while coding'
[INFO] Guide sections retrieved: ['lofi', 'ambient']
[INFO] Parsed profile (llm): {'favorite_genre': 'lofi', 'favorite_mood': 'focused', 'target_energy': 0.4, 'likes_acoustic': True}
[INFO] Retrieved 8 candidates: [(9, 4.39), (4, 3.38), (2, 3.33), (7, 1.42), (6, 1.34), (19, 1.3), (18, 1.29), (12, 1.27)]
[INFO] Final picks (llm): [9, 2, 4]
================================================================
Request: background music while coding
  profile (llm): genre=lofi  mood=focused  energy=0.40  acoustic=True
================================================================
Here are the top lofi picks tailored for coding, featuring steady beats and instrumental warmth to keep you focused without distractions.

1. Focus Flow — LoRoom  (lofi, focused, energy 0.40)
     With its focused mood, steady energy of 0.40, and high acousticness, 'Focus Flow' is the ideal instrumental soundtrack for coding.  [confidence 0.98]
2. Midnight Coding — LoRoom  (lofi, chill, energy 0.42)
     'Midnight Coding' delivers a chill lofi vibe with a balanced energy level of 0.42 that keeps you in the zone.  [confidence 0.92]
3. Library Rain — Paper Lanterns  (lofi, chill, energy 0.35)
     'Library Rain' offers a gentle acoustic lofi texture and a low energy of 0.35 to maintain deep concentration.  [confidence 0.88]

[answer: llm | retrieved 8 songs | guide notes: lofi, ambient]

```

## 5. Offline mode (no API key) and offline evaluation

```
$ python -m src.main --offline "late night drive through the city" -k 3
(offline mode: keyword parsing + rule-based explanations)

================================================================
Request: late night drive through the city
  profile (keywords): genre=synthwave  mood=moody  energy=0.75  acoustic=False
================================================================
Top matches from the rule-based scorer.

1. Night Drive Loop — Neon Echo  (synthwave, moody, energy 0.75)
     genre match: synthwave (+2.0); mood match: moody (+1.0); energy 0.75 vs target 0.75 (+1.00); non-acoustic fit (+0.39)
2. Concrete Crown — Mic Atlas  (hip hop, confident, energy 0.78)
     energy 0.78 vs target 0.75 (+0.97); non-acoustic fit (+0.46)
3. Sunrise City — Neon Echo  (pop, happy, energy 0.82)
     energy 0.82 vs target 0.75 (+0.93); non-acoustic fit (+0.41)

[answer: template | retrieved 8 songs | guide notes: synthwave, lofi, r&b]

```

```
$ python -m src.evaluate --offline

=== baseline (offline), songs only ===
request                                    hit@1  prec  n energy grnd  fb result
upbeat happy pop for a road trip               Y  0.60  5      Y    Y   Y   PASS
chill lofi beats to study to                   Y  0.80  5      Y    Y   Y   PASS
something intense and loud for the gym         Y  0.40  5      Y    Y   Y   PASS
calm piano music to fall asleep to             Y  0.40  5      Y    Y   Y   PASS
sad acoustic songs for a rainy day             Y  0.20  5      Y    Y   Y   PASS
romantic slow jams for date night              Y  0.20  5      Y    Y   Y   PASS
party music to dance to                        Y  0.60  5      Y    Y   Y   PASS
nostalgic country tunes for a long drive       Y  0.20  5      Y    Y   Y   PASS
smooth jazz to unwind after work               Y  0.20  5      N    Y   Y   FAIL
background music while coding                  N  0.00  5      N    Y   Y   FAIL
beach party vibes                              Y  0.60  5      Y    Y   Y   PASS
late night drive through the city              N  0.20  5      Y    Y   Y   FAIL
k-pop for a euphoric mood                      -     -  5      Y    Y   Y   PASS
afrobeats for a summer cookout                 -     -  5      Y    Y   Y   PASS
PASSED 11/14
summary: {"passed": "11/14", "cases": 14, "runs_per_case": 1, "hit_at_1": 0.83, "precision": 0.37, "avg_picks": 5, "energy_fit": 0.86, "grounded": 1, "weak_match_flagged": 1, "consistency": 1, "fallback_rate": 1, "avg_confidence": null, "confidence_when_fit": null, "confidence_when_not_fit": null}

=== baseline (offline), songs + guide ===
request                                    hit@1  prec  n energy grnd  fb result
upbeat happy pop for a road trip               Y  0.60  5      Y    Y   Y   PASS
chill lofi beats to study to                   Y  0.80  5      Y    Y   Y   PASS
something intense and loud for the gym         Y  0.40  5      Y    Y   Y   PASS
calm piano music to fall asleep to             Y  0.60  5      Y    Y   Y   PASS
sad acoustic songs for a rainy day             Y  0.20  5      Y    Y   Y   PASS
romantic slow jams for date night              Y  0.20  5      Y    Y   Y   PASS
party music to dance to                        Y  0.80  5      Y    Y   Y   PASS
nostalgic country tunes for a long drive       Y  0.20  5      Y    Y   Y   PASS
smooth jazz to unwind after work               Y  0.20  5      Y    Y   Y   PASS
background music while coding                  Y  0.80  5      Y    Y   Y   PASS
beach party vibes                              Y  0.80  5      Y    Y   Y   PASS
late night drive through the city              Y  0.20  5      Y    Y   Y   PASS
k-pop for a euphoric mood                      -     -  5      Y    Y   Y   PASS
afrobeats for a summer cookout                 -     -  5      Y    Y   Y   PASS
PASSED 14/14
summary: {"passed": "14/14", "cases": 14, "runs_per_case": 1, "hit_at_1": 1, "precision": 0.48, "avg_picks": 5, "energy_fit": 1, "grounded": 1, "weak_match_flagged": 1, "consistency": 1, "fallback_rate": 1, "avg_confidence": null, "confidence_when_fit": null, "confidence_when_not_fit": null}

Full report saved to logs/eval_report.json and docs/evaluation_results.md
```

Full live evaluation results (all four configurations): [evaluation_results.md](evaluation_results.md).

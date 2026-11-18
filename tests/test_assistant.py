"""Tests for the RAG pipeline and guardrails. A fake LLM stands in for Gemini."""

import pytest

from src.assistant import (
    clean_profile,
    keyword_parse,
    recommend_from_text,
    validate_picks,
    validate_request,
)
from src.llm_client import LLMError, parse_json_text
from src.recommender import load_songs

SONGS = load_songs("data/songs.csv")
GENRES = sorted({s["genre"] for s in SONGS})
MOODS = sorted({s["mood"] for s in SONGS})


class FakeLLM:
    """Returns scripted responses in order; an Exception in the script is raised."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_json(self, prompt, temperature=0.0):
        self.prompts.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


LOFI_PROFILE = {"favorite_genre": "lofi", "favorite_mood": "chill", "target_energy": 0.4, "likes_acoustic": True}


# --- guardrails ------------------------------------------------------------

def test_validate_request_rejects_empty_and_too_long():
    with pytest.raises(ValueError):
        validate_request("   ")
    with pytest.raises(ValueError):
        validate_request("a" * 301)
    assert validate_request("  chill   lofi ") == "chill lofi"


def test_clean_profile_clamps_energy_and_flags_unknown_genre():
    profile, warnings = clean_profile(
        {"favorite_genre": "K-Pop", "favorite_mood": "happy", "target_energy": 1.5, "likes_acoustic": "yes"},
        GENRES, MOODS,
    )
    assert profile["target_energy"] == 1.0
    assert profile["favorite_genre"] == "k-pop"
    assert profile["likes_acoustic"] is True
    assert any("k-pop" in w for w in warnings)
    assert any("clamped" in w for w in warnings)


def test_keyword_parse_prefers_longest_genre_and_sets_energy():
    profile = keyword_parse("some chill indie pop for studying", GENRES, MOODS)
    assert profile["favorite_genre"] == "indie pop"
    assert profile["favorite_mood"] == "chill"
    assert profile["target_energy"] < 0.5


def test_parse_json_text_handles_code_fences():
    assert parse_json_text('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_text("[1, 2]") == [1, 2]
    with pytest.raises(LLMError):
        parse_json_text("not json")
    with pytest.raises(LLMError):
        parse_json_text('"just a string"')


# --- retrieval-grounded generation -----------------------------------------

def test_validate_picks_drops_ids_outside_candidates():
    candidates = [(s, 3.0, "") for s in SONGS[:3]]
    raw = {"picks": [{"id": SONGS[0]["id"], "why": "fits"}, {"id": 999, "why": "made up"}, {"id": SONGS[0]["id"]}]}
    picks, dropped = validate_picks(raw, candidates, k=5)
    assert [p.song["id"] for p in picks] == [SONGS[0]["id"]]
    assert 999 in dropped


def test_validate_picks_clamps_confidence():
    candidates = [(s, 3.0, "") for s in SONGS[:3]]
    raw = {"picks": [{"id": SONGS[0]["id"], "confidence": 1.7},
                     {"id": SONGS[1]["id"], "confidence": "high"},
                     {"id": SONGS[2]["id"], "confidence": 0.64}]}
    picks, _ = validate_picks(raw, candidates, k=5)
    assert [p.confidence for p in picks] == [1.0, None, 0.64]


def test_llm_pipeline_uses_retrieved_songs_only():
    lofi_ids = [s["id"] for s in SONGS if s["genre"] == "lofi"]
    llm = FakeLLM(
        LOFI_PROFILE,
        {"picks": [{"id": lofi_ids[0], "why": "calm lofi"}, {"id": 12345, "why": "hallucinated"}],
         "summary": "Calm picks."},
    )
    result = recommend_from_text("chill beats to study to", SONGS, llm=llm, k=3)

    assert result.profile_source == "llm" and result.answer_source == "llm"
    assert [p.song["id"] for p in result.picks] == [lofi_ids[0]]
    assert result.dropped_ids == [12345]
    # The answer prompt must contain the retrieved candidates (that is the "augmented" part).
    assert "Candidates:" in llm.prompts[1] and f"id={lofi_ids[0]}" in llm.prompts[1]


def test_bare_list_answer_is_accepted():
    lofi_ids = [s["id"] for s in SONGS if s["genre"] == "lofi"]
    llm = FakeLLM([LOFI_PROFILE], [{"id": lofi_ids[0], "why": "calm", "confidence": 0.9}])
    result = recommend_from_text("chill beats to study to", SONGS, llm=llm, k=3)
    assert result.profile_source == "llm" and result.answer_source == "llm"
    assert result.picks[0].confidence == 0.9


def test_llm_declining_keeps_its_message_and_flags_weak_match():
    llm = FakeLLM(LOFI_PROFILE, {"picks": [], "summary": "Nothing in the catalog fits afrobeats."})
    result = recommend_from_text("afrobeats for a cookout", SONGS, llm=llm, k=3)
    assert result.answer_source == "llm_no_match"
    assert result.summary == "Nothing in the catalog fits afrobeats."
    assert result.weak_match is True
    assert len(result.picks) == 3  # closest songs still shown, labelled by the warning


def test_llm_failure_falls_back_to_keywords_and_template():
    llm = FakeLLM(LLMError("down"), LLMError("down"))
    result = recommend_from_text("chill lofi to study", SONGS, llm=llm, k=3)
    assert result.profile_source == "keywords"
    assert result.answer_source == "template"
    assert len(result.picks) == 3
    assert result.picks[0].song["genre"] == "lofi"


def test_offline_mode_flags_out_of_catalog_request():
    result = recommend_from_text("k-pop that feels euphoric", SONGS, llm=None)
    assert result.weak_match is True
    assert len(result.picks) == 5


# --- second retrieval source: genre guide ------------------------------------

from src.knowledge import load_guide, retrieve_guide  # noqa: E402

GUIDE = load_guide()


def test_guide_covers_every_catalog_genre():
    guide_genres = {s.name for s in GUIDE if s.kind == "genre"}
    assert set(GENRES) <= guide_genres


def test_guide_retrieves_by_activity_and_not_inside_hyphens():
    assert retrieve_guide("background music while coding", GUIDE)[0].name == "lofi"
    assert retrieve_guide("late night drive through the city", GUIDE)[0].name == "synthwave"
    names = [s.name for s in retrieve_guide("k-pop for a euphoric mood", GUIDE)]
    assert names[0] == "k-pop" and "pop" not in names


def test_guide_fills_offline_profile_for_activity_request():
    without = recommend_from_text("background music while coding", SONGS, llm=None)
    with_guide = recommend_from_text("background music while coding", SONGS, llm=None, guide=GUIDE)
    assert without.profile["favorite_genre"] == ""
    assert with_guide.profile["favorite_genre"] == "lofi"
    assert with_guide.picks[0].song["genre"] == "lofi"


def test_guide_flags_missing_genre_even_if_llm_maps_it():
    llm = FakeLLM({"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8, "likes_acoustic": False},
                  {"picks": [{"id": 1, "why": "closest pop"}], "summary": "No K-pop here."})
    result = recommend_from_text("k-pop for a euphoric mood", SONGS, llm=llm, guide=GUIDE)
    assert result.weak_match is True
    assert any("k-pop" in w for w in result.warnings)
    assert "NOT IN CATALOG" in llm.prompts[0] and "NOT IN CATALOG" in llm.prompts[1]

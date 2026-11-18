"""
Command line runner for the AI Music Recommender.

Run from the project root:
    python -m src.main "chill songs for studying"   # one request
    python -m src.main                              # interactive prompt
    python -m src.main --offline "upbeat pop"       # no API key needed
    python -m src.main --demo                       # Module 3 profile demo
"""

import argparse
import logging
import os
import sys

try:
    from src.assistant import AssistantResult, recommend_from_text  # python -m src.main
    from src.llm_client import GeminiClient, LLMError
    from src.recommender import load_songs, recommend_songs
except ImportError:
    from assistant import AssistantResult, recommend_from_text  # python src/main.py
    from llm_client import GeminiClient, LLMError
    from recommender import load_songs, recommend_songs

CATALOG_PATH = "data/songs.csv"
LOG_PATH = os.path.join("logs", "assistant.log")


# Taste profiles. Keys match the UserProfile dataclass fields in recommender.py.
PROFILES = {
    # --- Core profiles ---
    # Default profile: upbeat, energetic pop listener.
    "High-Energy Pop": {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.80,
        "likes_acoustic": False,
    },
    # "Late-night study" listener who wants calm, acoustic, chill lofi.
    "Chill Lofi": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.40,
        "likes_acoustic": True,
    },
    "Deep Intense Rock": {
        "favorite_genre": "rock",
        "favorite_mood": "intense",
        "target_energy": 0.90,
        "likes_acoustic": False,
    },
    # --- Adversarial / edge-case profiles ---
    # Conflicting: sad mood but very high energy (sad songs in the catalog are calm).
    "EDGE: Sad but Hyped": {
        "favorite_genre": "edm",
        "favorite_mood": "sad",
        "target_energy": 0.90,
        "likes_acoustic": False,
    },
    # Conflicting: wants metal energy but also acoustic sound.
    "EDGE: Acoustic Headbanger": {
        "favorite_genre": "metal",
        "favorite_mood": "angry",
        "target_energy": 0.95,
        "likes_acoustic": True,
    },
    # Genre and mood that don't exist in the catalog.
    "EDGE: Ghost Genre": {
        "favorite_genre": "k-pop",
        "favorite_mood": "euphoric",
        "target_energy": 0.50,
        "likes_acoustic": False,
    },
    # Invalid input: energy outside the 0-1 range.
    "EDGE: Out-of-Range Energy": {
        "favorite_genre": "classical",
        "favorite_mood": "peaceful",
        "target_energy": 1.50,
        "likes_acoustic": True,
    },
}

WIDTH = 64


def print_recommendations(name: str, user_prefs: dict, recommendations: list) -> None:
    """Prints one profile's top-k results as a readable block."""
    print("=" * WIDTH)
    print(f"Profile: {name}")
    print(
        f"  genre={user_prefs['favorite_genre']}  mood={user_prefs['favorite_mood']}  "
        f"energy={user_prefs['target_energy']:.2f}  acoustic={user_prefs['likes_acoustic']}"
    )
    print("=" * WIDTH)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"{rank}. {song['title']} — {song['artist']}")
        print(f"   Score: {score:.2f} / 4.50   ({song['genre']}, {song['mood']})")
        for reason in explanation.split("; "):
            print(f"     • {reason}")
        print()


def setup_logging(verbose: bool = False) -> None:
    """Logs every pipeline step to logs/assistant.log; warnings also go to the console."""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logger = logging.getLogger("music_assistant")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(file_handler)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO if verbose else logging.WARNING)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)


def make_llm(offline: bool):
    """Returns a GeminiClient, or None (offline mode) if disabled or not configured."""
    if offline:
        return None
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    try:
        return GeminiClient()
    except LLMError as exc:
        logging.getLogger("music_assistant").warning("%s Falling back to offline mode.", exc)
        return None


def print_result(result: AssistantResult) -> None:
    """Prints an assistant answer with its profile, picks and any warnings."""
    p = result.profile
    print("=" * WIDTH)
    print(f"Request: {result.request}")
    print(
        f"  profile ({result.profile_source}): genre={p['favorite_genre'] or '-'}  mood={p['favorite_mood'] or '-'}  "
        f"energy={p['target_energy']:.2f}  acoustic={p['likes_acoustic']}"
    )
    print("=" * WIDTH)
    for warning in result.warnings:
        print(f"  ! {warning}")
    if result.summary:
        print(result.summary)
    print()
    for rank, pick in enumerate(result.picks, start=1):
        song = pick.song
        print(f"{rank}. {song['title']} — {song['artist']}  ({song['genre']}, {song['mood']}, energy {song['energy']:.2f})")
        confidence = f"  [confidence {pick.confidence:.2f}]" if pick.confidence is not None else ""
        print(f"     {pick.why}{confidence}")
    print(f"\n[answer: {result.answer_source} | retrieved {len(result.candidates)} candidates]\n")


def run_demo(songs) -> None:
    """Module 3 behaviour: score the fixed profiles with the rule-based recommender."""
    for name, user_prefs in PROFILES.items():
        recommendations = recommend_songs(user_prefs, songs, k=5)
        print_recommendations(name, user_prefs, recommendations)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI music recommender (RAG over data/songs.csv).")
    parser.add_argument("request", nargs="*", help="what you want to listen to, in plain English")
    parser.add_argument("-k", type=int, default=5, help="number of songs to recommend (1-8)")
    parser.add_argument("--offline", action="store_true", help="skip Gemini; use keyword parsing and scorer explanations")
    parser.add_argument("--demo", action="store_true", help="run the Module 3 fixed-profile demo")
    parser.add_argument("--verbose", action="store_true", help="print pipeline log lines to the console")
    args = parser.parse_args()

    setup_logging(args.verbose)
    songs = load_songs(CATALOG_PATH)

    if args.demo:
        print(f"Loaded songs: {len(songs)}\n")
        run_demo(songs)
        return

    k = min(max(args.k, 1), 8)
    llm = make_llm(args.offline)
    if llm is None:
        print("(offline mode: keyword parsing + rule-based explanations)\n")

    def handle(text: str) -> None:
        try:
            print_result(recommend_from_text(text, songs, llm=llm, k=k))
        except ValueError as exc:
            print(f"Invalid request: {exc}")

    if args.request:
        handle(" ".join(args.request))
        return

    print("Describe what you want to hear (blank line or Ctrl-D to quit).")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            break
        handle(text)


if __name__ == "__main__":
    main()

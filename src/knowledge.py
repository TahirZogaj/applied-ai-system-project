"""
Second retrieval source: the custom genre guide (data/genre_guide.md).

The guide is split into one document per "## " section. Retrieval scores each
section by how many of the request's words appear in its name and keywords,
so requests like "music for coding" can find lofi even though they never
name a genre. Sections of type "missing" describe genres that are NOT in the
catalog, which lets the system say so instead of guessing.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger("music_assistant")

GUIDE_PATH = "data/genre_guide.md"
STOPWORDS = {
    "a", "an", "and", "the", "for", "to", "of", "in", "on", "with", "some", "something", "songs",
    "song", "music", "tunes", "tracks", "me", "my", "i", "want", "like", "that", "is", "it", "while",
    "play", "give", "recommend", "please", "good", "best", "kind", "type", "vibe", "vibes", "mood",
}


@dataclass
class GuideSection:
    name: str
    kind: str                        # "genre" or "missing"
    moods: List[str] = field(default_factory=list)
    energy: float = 0.5
    acoustic: bool = False
    nearest: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    text: str = ""

    def as_note(self) -> str:
        """Compact text form used inside prompts."""
        if self.kind == "missing":
            return f"[{self.name}] NOT IN CATALOG; nearest catalog genres: {', '.join(self.nearest)}. {self.text}"
        return (f"[{self.name}] moods: {', '.join(self.moods)}; typical energy {self.energy:.2f}; "
                f"acoustic: {'yes' if self.acoustic else 'no'}. {self.text}")


def _split_list(value: str) -> List[str]:
    return [v.strip().lower() for v in value.split(",") if v.strip()]


def load_guide(path: str = GUIDE_PATH) -> List[GuideSection]:
    """Parses the guide markdown into sections."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    sections: List[GuideSection] = []
    for block in content.split("\n## ")[1:]:
        lines = block.strip().splitlines()
        section = GuideSection(name=lines[0].strip().lower(), kind="genre")
        prose = []
        for line in lines[1:]:
            key, sep, value = line.partition(":")
            key = key.strip().lower()
            if sep and key in {"type", "moods", "energy", "acoustic", "nearest", "keywords"}:
                if key == "type":
                    section.kind = value.strip().lower()
                elif key == "energy":
                    section.energy = float(value)
                elif key == "acoustic":
                    section.acoustic = value.strip().lower() == "yes"
                else:
                    setattr(section, key, _split_list(value))
            elif line.strip():
                prose.append(line.strip())
        section.text = " ".join(prose)
        sections.append(section)
    return sections


def _tokens(text: str) -> List[str]:
    # Keep hyphenated and "&" words intact so "k-pop" and "r&b" stay single tokens.
    return [t for t in re.findall(r"[a-z0-9&]+(?:-[a-z0-9]+)*", text.lower()) if t not in STOPWORDS]


def _stem(word: str) -> str:
    for suffix in ("ing", "es", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _mentions(text: str, term: str) -> bool:
    """Whole-word match that treats hyphens as part of a word ("k-pop" is not "pop")."""
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", text.lower()) is not None


def section_score(request: str, section: GuideSection) -> float:
    """Name mention = 3 points; each distinct keyword match = 1 point."""
    score = 3.0 if _mentions(request, section.name) else 0.0
    request_stems = {_stem(t) for t in _tokens(request)}
    for keyword in section.keywords:
        if " " in keyword:
            if _mentions(request, keyword):
                score += 1.0
        elif _stem(keyword) in request_stems:
            score += 1.0
    return score


def retrieve_guide(request: str, guide: List[GuideSection], n: int = 3) -> List[GuideSection]:
    """Returns up to n guide sections relevant to the request, best first."""
    scored = [(section_score(request, s), s) for s in guide]
    hits = [s for score, s in sorted(scored, key=lambda x: x[0], reverse=True) if score > 0][:n]
    logger.info("Guide sections retrieved: %s", [s.name for s in hits])
    return hits


def guide_hints(sections: List[GuideSection]) -> Dict[str, object]:
    """Profile hints from the best in-catalog section (used by the offline parser)."""
    for s in sections:
        if s.kind == "genre":
            return {"favorite_genre": s.name, "favorite_mood": s.moods[0] if s.moods else "",
                    "target_energy": s.energy, "likes_acoustic": s.acoustic}
        if s.kind == "missing" and s.nearest:
            return {"favorite_genre": s.nearest[0], "favorite_mood": "", "target_energy": 0.5,
                    "likes_acoustic": False}
    return {}

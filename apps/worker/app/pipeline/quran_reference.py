"""
pipeline/quran_reference.py

Local, offline Quran reference dataset for verifying "quran"-classified
transcript segments against authoritative text (with full tashkeel),
instead of trusting the LLM's own reproduction.

Reads from a locally-saved JSON file (packages/prompts/arabic/quran.json)
-- confirmed structure: a list of surah objects, each with
{"id", "name", "transliteration", "type", "total_verses", "verses"},
where "verses" is a list of {"id", "text"} objects (ayah number + full
tashkeel text).

Matching happens entirely offline once loaded -- no per-request network
dependency in production, no external API rate limits, deterministic
and testable.
"""

import difflib
import json
import re
from pathlib import Path

# Adjust this if your actual folder depth differs from the scaffolded
# structure: apps/worker/app/pipeline/quran_reference.py -> up 4 levels
# -> repo root -> packages/prompts/arabic/quran.json
DATA_PATH = Path(__file__).resolve().parents[4] / "packages" / "prompts" / "arabic" / "quran.json"

# Similarity ratio (0-1) below which we refuse to trust a match.
# Raised from an initial guess of 0.5 to 0.8 after testing: every
# genuinely correct match scored 0.97-1.0, while a deliberately
# non-Quranic but similar-sounding phrase scored 0.65 -- a false
# positive at lower thresholds. 0.8 keeps real matches while
# rejecting that kind of near-miss.
MATCH_THRESHOLD = 0.8

_ayah_cache: list[dict] | None = None


def _flatten_dataset(raw: list[dict]) -> list[dict]:
    """
    Flattens the surah-nested structure into one list of
    {"surah_id", "surah_name", "ayah_id", "text"} dicts -- one per ayah
    -- so matching can scan the whole Quran without caring about surah
    boundaries.
    """
    flat = []
    for surah in raw:
        surah_id = surah.get("id")
        surah_name = surah.get("name")
        for verse in surah.get("verses", []):
            flat.append({
                "surah_id": surah_id,
                "surah_name": surah_name,
                "ayah_id": verse.get("id"),
                "text": verse.get("text", ""),
            })
    return flat


def _load_ayat() -> list[dict]:
    global _ayah_cache
    if _ayah_cache is not None:
        return _ayah_cache

    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Quran dataset not found at {DATA_PATH}. Check DATA_PATH matches "
            f"where you actually saved quran.json."
        )

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    _ayah_cache = _flatten_dataset(raw)
    return _ayah_cache


_DIACRITICS = re.compile(r'[\u0610-\u061A\u064B-\u065F\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]')


def normalize_arabic(text: str) -> str:
    """Strips tashkeel and normalizes common letter variants, for matching purposes only."""
    # Dagger alef (superscript alef, U+0670) represents an actual elided
    # ا letter in Uthmani spelling (e.g. "السَّمَٰوَٰتِ" -> "السماوات" in
    # standard spelling) -- convert it, don't strip it as if it were
    # pure decoration like the other diacritics below. Stripping it
    # instead of converting caused a genuine partial-quote match to
    # score too low to clear MATCH_THRESHOLD during testing.
    text = text.replace('\u0670', 'ا')
    text = _DIACRITICS.sub('', text)
    text = re.sub(r'[إأآٱا]', 'ا', text)
    text = text.replace('ى', 'ي')
    text = text.replace('ة', 'ه')
    text = re.sub(r'ـ+', '', text)  # tatweel
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _containment_score(candidate: str, ayah: str) -> float:
    """
    How much of `candidate` is found as a contiguous match within
    `ayah`, regardless of the ayah's total length. This is what makes
    PARTIAL quotes of a long ayah score well -- whole-string ratio()
    alone would dilute a short, exact excerpt against a much longer
    ayah and miss it.
    """
    if not candidate:
        return 0.0
    matcher = difflib.SequenceMatcher(None, candidate, ayah)
    match = matcher.find_longest_match(0, len(candidate), 0, len(ayah))
    return match.size / len(candidate)


def find_matching_ayah(candidate_text: str) -> dict | None:
    """
    Returns the best-matching ayah as a dict:
        {"surah_id", "surah_name", "ayah_id", "text", "score"}
    where "text" is the authoritative full-tashkeel wording, or None if
    nothing clears MATCH_THRESHOLD.

    Uses the MAX of two scores per candidate ayah:
      - whole-string ratio (best for a full-ayah quote)
      - containment score (best for a partial/mid-ayah quote)

    KNOWN, ACCEPTED BEHAVIOR: if a phrase is repeated verbatim in more
    than one place in the Quran (e.g. the refrain in Surah Ar-Rahman,
    or the near-identical closing phrase shared by 2:255 and 42:4),
    this returns whichever scores highest -- which may not be the
    specific occurrence you had in mind, but is still a genuinely
    correct citation of that exact wording. This is not a bug to fix;
    the Quran itself contains repeated/near-identical phrasing across
    different surahs.
    """
    ayat = _load_ayat()
    normalized_candidate = normalize_arabic(candidate_text)

    best_match, best_score = None, 0.0
    for entry in ayat:
        normalized_ayah = normalize_arabic(entry["text"])
        ratio_score = difflib.SequenceMatcher(None, normalized_candidate, normalized_ayah).ratio()
        containment = _containment_score(normalized_candidate, normalized_ayah)
        score = max(ratio_score, containment)
        if score > best_score:
            best_score, best_match = score, entry

    if best_match is not None and best_score >= MATCH_THRESHOLD:
        return {**best_match, "score": best_score}
    return None
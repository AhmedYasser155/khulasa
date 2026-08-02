"""
pipeline/refine_transcript.py

Stage 2.5: Refine transcript (runs after transcribe, before score).

Sends the raw Whisper transcript to an LLM to:
  1. Correct likely ASR mis-transcriptions using surrounding context
  2. Flag segments that are Quranic ayat, Hadith, or well-known Arabic
     quotes/proverbs via a "content_type" field, so captions.py can
     style them differently (different color/weight per type)

IMPORTANT DESIGN DECISION: the LLM is explicitly instructed NOT to
rewrite Quranic text from its own "memory" -- it only classifies a
segment as Quran. quran_reference.find_matching_ayah() then looks up
the actual verse from a local, offline dataset (not the LLM, not a
live third-party API) to replace it with the authoritative wording.
Never trust an LLM's own reproduction of scripture as authoritative --
use it purely as a classifier for this, not a source of the text
itself. Small hallucinated word changes in a sacred text are a much
more serious problem than a wrong word in ordinary speech.
"""

import json
from pathlib import Path

from groq import Groq

from app.pipeline import quran_reference

MODEL = "llama-3.3-70b-versatile"
PROMPT_PATH = Path(__file__).resolve().parents[4] / "packages" / "prompts" / "arabic" / "refine_transcript.md"


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _format_segments_for_prompt(segments: list[dict]) -> str:
    lines = []
    for i, seg in enumerate(segments):
        lines.append(f"{i}: {seg.get('text', '').strip()}")
    return "\n".join(lines)


def refine_transcript(transcript: dict, verify_quran: bool = False) -> dict:
    """
    Returns a new transcript dict with the same segment count/order/
    timestamps as the input, but corrected text and an added
    "content_type" field per segment: "quran" | "hadith" | "quote" | "normal".

    verify_quran=False by default until quran_reference.find_matching_ayah()
    has been validated via test_quran_reference.py -- with it off,
    "quran"-classified segments keep the LLM's (uncorrected, original)
    ASR text rather than a verified one, which is the safer default
    until that matching is proven reliable on your own content.
    """
    segments = transcript.get("segments", [])
    if not segments:
        return transcript

    system_prompt = _load_system_prompt()
    segments_text = _format_segments_for_prompt(segments)

    client = Groq()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": segments_text},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,  # low temperature -- correction/classification, not creative writing
    )

    result = json.loads(response.choices[0].message.content)
    refined_segments = result.get("segments", [])

    # Defensive: if the model didn't return exactly one entry per
    # original segment, OR the indices don't form a clean 0..N-1 set
    # (meaning something got duplicated/skipped/reordered in a way we
    # can't safely trust), refuse to use the result rather than risk
    # silently pairing the wrong correction with the wrong segment.
    expected_indices = set(range(len(segments)))
    returned_indices = {r.get("index") for r in refined_segments}
    if len(refined_segments) != len(segments) or returned_indices != expected_indices:
        return transcript

    # Match by the model's own "index" field rather than trusting
    # array position -- protects against silent misalignment if the
    # model ever returns entries in a different order than it received them.
    refined_by_index = {r["index"]: r for r in refined_segments}

    new_segments = []
    for i, original in enumerate(segments):
        refined = refined_by_index[i]
        content_type = refined.get("content_type", "normal")

        if content_type == "quran":
            # Never trust the LLM's own reproduction of scripture --
            # keep the original ASR text unless a verified local match
            # replaces it.
            corrected_text = original.get("text", "")
            quran_match = None
            if verify_quran:
                quran_match = quran_reference.find_matching_ayah(corrected_text)
                if quran_match:
                    corrected_text = quran_match["text"]
        else:
            corrected_text = refined.get("corrected_text", original.get("text", ""))
            quran_match = None

        new_segment = {
            **original,
            "text": corrected_text,
            "content_type": content_type,
        }
        if quran_match:
            # Keep the surah/ayah reference and match confidence around --
            # useful for later review, and for showing a citation if the
            # frontend ever wants to display "Surah X, Ayah Y" on the clip.
            new_segment["quran_reference"] = {
                "surah_id": quran_match["surah_id"],
                "surah_name": quran_match["surah_name"],
                "ayah_id": quran_match["ayah_id"],
                "match_score": quran_match["score"],
            }

        new_segments.append(new_segment)

    return {**transcript, "segments": new_segments}
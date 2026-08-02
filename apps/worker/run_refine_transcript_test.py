#!/usr/bin/env python3
"""
test_refine_transcript.py

Standalone test for the transcript refinement + Quran/Hadith/quote
classification stage, following the same "test it alone before it
touches a real job" discipline as every other pipeline piece.

Setup:
    pip install groq requests python-dotenv

Uses transcription_result.json (from test_whisper_arabic.py) as input.

Usage:
    python test_refine_transcript.py
"""

import json
import os

from dotenv import load_dotenv
load_dotenv()

from app.pipeline.refine_transcript import refine_transcript  # adjust import if run outside apps/worker

TRANSCRIPT_JSON_PATH = "transcription_result.json"


def main():
    if not os.path.isfile(TRANSCRIPT_JSON_PATH):
        print(f"Transcript not found: {TRANSCRIPT_JSON_PATH}. Run test_whisper_arabic.py first.")
        return

    with open(TRANSCRIPT_JSON_PATH, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    original_segments = transcript.get("segments", [])
    print(f"Loaded {len(original_segments)} segments. Refining...\n")

    refined = refine_transcript(transcript, verify_quran=True)
    refined_segments = refined.get("segments", [])

    if len(refined_segments) != len(original_segments):
        print("WARNING: segment count changed -- refinement was rejected, original returned unchanged.")
        return

    print("=" * 70)
    for i, (orig, new) in enumerate(zip(original_segments, refined_segments)):
        changed = orig.get("text", "").strip() != new.get("text", "").strip()
        content_type = new.get("content_type", "normal")
        marker = f"[{content_type.upper()}]" if content_type != "normal" else ""
        change_marker = " (CHANGED)" if changed else ""

        print(f"#{i} {marker}{change_marker}")
        if changed:
            print(f"  before: {orig.get('text', '').strip()}")
            print(f"  after:  {new.get('text', '').strip()}")
        else:
            print(f"  text:   {new.get('text', '').strip()}")
        print()

    quran_count = sum(1 for s in refined_segments if s.get("content_type") == "quran")
    hadith_count = sum(1 for s in refined_segments if s.get("content_type") == "hadith")
    quote_count = sum(1 for s in refined_segments if s.get("content_type") == "quote")
    changed_count = sum(
        1 for o, n in zip(original_segments, refined_segments)
        if o.get("text", "").strip() != n.get("text", "").strip()
    )

    print("=" * 70)
    print(f"Segments corrected: {changed_count}/{len(original_segments)}")
    print(f"Classified as Quran: {quran_count}")
    print(f"Classified as Hadith: {hadith_count}")
    print(f"Classified as Quote: {quote_count}")
    print("=" * 70)
    print("\nCheck each classification and correction by eye -- this is exactly")
    print("the kind of output that needs human review before trusting it,")
    print("especially any 'quran' classification and any 'CHANGED' text.")

    out_path = "refined_transcript_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(refined, f, ensure_ascii=False, indent=2)
    print(f"\nFull result saved to {out_path}")


if __name__ == "__main__":
    main()
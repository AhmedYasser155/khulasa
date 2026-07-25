#!/usr/bin/env python3
"""
test_whisper_arabic.py

Standalone test for Groq-hosted Whisper large-v3 Arabic transcription.
No project dependencies needed beyond the `groq` package -- this is
meant to be run completely on its own, before any pipeline wiring.

Setup (Windows PowerShell):

    pip install groq python-dotenv
    $env:GROQ_API_KEY = "your_key_here"     # get one free at console.groq.com

Usage:

    python test_whisper_arabic.py

Edit AUDIO_PATH below to point at your file.
Supported audio formats: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm
"""

import os
import json

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- Hardcoded input path. Change this to test a different file/dialect. ---
#C:\Users\aayasser\Desktop\PLAYGROUND\khulasa\playground\tests\whisper\2.mp3
AUDIO_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\khulasa\playground\tests\whisper\2.mp3"


def transcribe_arabic(audio_path: str) -> dict:
    client = Groq()  # reads GROQ_API_KEY from environment automatically

    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f.read()),
            model="whisper-large-v3",
            language="ar",                     # ISO-639-1 hint improves accuracy/latency
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
            temperature=0.0,
        )

    # transcription is an SDK object; convert to plain dict for easy inspection
    return transcription.model_dump() if hasattr(transcription, "model_dump") else dict(transcription)


def main():
    if not os.path.isfile(AUDIO_PATH):
        print(f"File not found: {AUDIO_PATH}")
        return

    if not os.environ.get("GROQ_API_KEY"):
        print("GROQ_API_KEY is not set. Run: $env:GROQ_API_KEY = \"your_key_here\"")
        return

    print(f"Transcribing: {AUDIO_PATH} ...\n")
    result = transcribe_arabic(AUDIO_PATH)

    print("=" * 60)
    print("FULL TEXT:")
    print("=" * 60)
    print(result.get("text", "").strip())

    print("\n" + "=" * 60)
    print("DETECTED LANGUAGE:", result.get("language", "n/a"))
    print("=" * 60)

    segments = result.get("segments", [])
    print(f"\nSegments: {len(segments)}")
    for seg in segments[:5]:
        print(f"  [{seg.get('start'):.2f}s - {seg.get('end'):.2f}s] {seg.get('text', '').strip()}")
    if len(segments) > 5:
        print(f"  ... and {len(segments) - 5} more (see full JSON below)")

    words = result.get("words", [])
    print(f"\nWord-level timestamps: {len(words)} words")
    for w in words[:10]:
        print(f"  [{w.get('start'):.2f}s - {w.get('end'):.2f}s] {w.get('word', '')}")
    if len(words) > 10:
        print(f"  ... and {len(words) - 10} more")

    # Dump full raw JSON to a file so you can inspect timestamps/structure in full
    out_path = "transcription_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nFull result saved to {out_path}")


if __name__ == "__main__":
    main()
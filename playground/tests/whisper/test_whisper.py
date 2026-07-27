#!/usr/bin/env python3
"""
test_whisper_arabic.py

Standalone test for Groq-hosted Whisper large-v3 Arabic transcription,
with automatic chunking for files that exceed Groq's 25MB upload limit.

For files under the limit, transcribes directly (fast path). For
larger files, splits the audio into chunks with FFmpeg (re-encoded to
a low, consistent bitrate so chunk size is predictable regardless of
the source file's original bitrate), transcribes each chunk, then
stitches all segments/words back together with corrected timestamps.

Setup (Windows PowerShell):

    winget install ffmpeg   (if not already installed)
    pip install groq python-dotenv
    $env:GROQ_API_KEY = "your_key_here"     # get one free at console.groq.com

Usage:

    python test_whisper_arabic.py

Edit SOURCE_PATH below to point at your file (audio or video).
"""

import os
import json
import subprocess
import tempfile

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- Hardcoded input path. Can be an audio file OR a video file --
# --- if it's a video, audio is extracted automatically first. ---
SOURCE_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\zatoona\playground\tests\media\sample_1min.mp4"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

# Groq's hard limit is 25MB. Stay comfortably under it.
MAX_UPLOAD_BYTES = 24 * 1024 * 1024
CHUNK_DURATION_SEC = 600           # 10 minutes per chunk
CHUNK_BITRATE = "64k"              # mono, 64kbps -> ~4.8MB per 10-min chunk, safely under the cap


def extract_audio_from_video(video_path: str) -> str:
    """
    Pulls just the audio track out of a video file into a standalone
    mp3. Much faster than sending the whole video through, since
    there's no video stream to decode/transfer at all.
    """
    audio_path = os.path.splitext(video_path)[0] + "_extracted_audio.mp3"
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                  # drop video stream entirely
        "-acodec", "libmp3lame",
        "-q:a", "2",             # good quality, reasonable file size
        audio_path,
    ]
    print(f"Extracting audio from video: {video_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed:\n{result.stderr[-1500:]}")
    print(f"Audio extracted to: {audio_path}\n")
    return audio_path


def resolve_audio_path(source_path: str) -> str:
    """Returns a usable audio file path, extracting from video first if needed."""
    ext = os.path.splitext(source_path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return extract_audio_from_video(source_path)
    return source_path


def get_audio_duration_sec(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def split_into_chunks(path: str, chunk_duration_sec: int, tmp_dir: str) -> list[str]:
    """Splits audio into fixed-duration, re-encoded chunks. Returns chunk file paths in order."""
    duration = get_audio_duration_sec(path)
    num_chunks = int(duration // chunk_duration_sec) + 1
    chunk_paths = []

    for i in range(num_chunks):
        start = i * chunk_duration_sec
        chunk_path = os.path.join(tmp_dir, f"chunk_{i:03d}.mp3")
        cmd = [
            "ffmpeg", "-y",
            "-i", path,
            "-ss", str(start),
            "-t", str(chunk_duration_sec),
            "-ac", "1",                 # mono
            "-b:a", CHUNK_BITRATE,
            chunk_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Skip chunks that ended up empty (can happen for the final chunk boundary)
        if os.path.isfile(chunk_path) and os.path.getsize(chunk_path) > 1000:
            chunk_paths.append(chunk_path)

    return chunk_paths


def transcribe_file(audio_path: str) -> dict:
    """Transcribes a single file (must already be under the size limit)."""
    client = Groq()
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f.read()),
            model="whisper-large-v3",
            language="ar",
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
            temperature=0.0,
        )
    return transcription.model_dump() if hasattr(transcription, "model_dump") else dict(transcription)


def transcribe_arabic(audio_path: str) -> dict:
    """
    Transcribes an Arabic audio file of any size. Chunks automatically
    if the file exceeds Groq's upload limit, and stitches results back
    together with corrected timestamps.
    """
    file_size = os.path.getsize(audio_path)

    if file_size <= MAX_UPLOAD_BYTES:
        print(f"File is {file_size / 1024 / 1024:.1f}MB -- under the limit, transcribing directly.")
        return transcribe_file(audio_path)

    print(f"File is {file_size / 1024 / 1024:.1f}MB -- exceeds Groq's 25MB limit, chunking...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        chunk_paths = split_into_chunks(audio_path, CHUNK_DURATION_SEC, tmp_dir)
        print(f"Split into {len(chunk_paths)} chunk(s) of ~{CHUNK_DURATION_SEC}s each.\n")

        combined_text_parts = []
        combined_segments = []
        combined_words = []
        detected_language = None

        for i, chunk_path in enumerate(chunk_paths):
            offset_sec = i * CHUNK_DURATION_SEC
            print(f"Transcribing chunk {i + 1}/{len(chunk_paths)} "
                  f"(offset +{offset_sec}s, size {os.path.getsize(chunk_path) / 1024:.0f}KB)...")

            result = transcribe_file(chunk_path)
            detected_language = detected_language or result.get("language")
            combined_text_parts.append(result.get("text", "").strip())

            for seg in result.get("segments", []):
                seg = dict(seg)
                seg["start"] = seg.get("start", 0) + offset_sec
                seg["end"] = seg.get("end", 0) + offset_sec
                combined_segments.append(seg)

            for w in result.get("words", []):
                w = dict(w)
                w["start"] = w.get("start", 0) + offset_sec
                w["end"] = w.get("end", 0) + offset_sec
                combined_words.append(w)

        return {
            "text": " ".join(combined_text_parts),
            "language": detected_language,
            "segments": combined_segments,
            "words": combined_words,
        }


def main():
    if not os.path.isfile(SOURCE_PATH):
        print(f"File not found: {SOURCE_PATH}")
        return

    if not os.environ.get("GROQ_API_KEY"):
        print("GROQ_API_KEY is not set. Run: $env:GROQ_API_KEY = \"your_key_here\"")
        return

    audio_path = resolve_audio_path(SOURCE_PATH)

    print(f"Transcribing: {audio_path} ...\n")
    result = transcribe_arabic(audio_path)

    print("\n" + "=" * 60)
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

    out_path = "transcription_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nFull result saved to {out_path}")


if __name__ == "__main__":
    main()
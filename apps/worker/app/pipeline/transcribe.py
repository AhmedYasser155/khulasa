"""
pipeline/transcribe.py

Stage 2: Transcribe (Arabic).

Migrated directly from test_whisper_arabic.py -- identical logic
(size check, chunking with re-encoding to a predictable bitrate,
timestamp-corrected stitching), just as an importable function
instead of a script with a hardcoded SOURCE_PATH and a main().
"""

import os
import subprocess
import tempfile

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MAX_UPLOAD_BYTES = 24 * 1024 * 1024
CHUNK_DURATION_SEC = 600
CHUNK_BITRATE = "64k"


def _get_audio_duration_sec(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def _split_into_chunks(path: str, chunk_duration_sec: int, tmp_dir: str) -> list[str]:
    duration = _get_audio_duration_sec(path)
    num_chunks = int(duration // chunk_duration_sec) + 1
    chunk_paths = []

    for i in range(num_chunks):
        start = i * chunk_duration_sec
        chunk_path = os.path.join(tmp_dir, f"chunk_{i:03d}.mp3")
        cmd = [
            "ffmpeg", "-y", "-i", path,
            "-ss", str(start), "-t", str(chunk_duration_sec),
            "-ac", "1", "-b:a", CHUNK_BITRATE,
            chunk_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        if os.path.isfile(chunk_path) and os.path.getsize(chunk_path) > 1000:
            chunk_paths.append(chunk_path)

    return chunk_paths


def _transcribe_file(audio_path: str) -> dict:
    """Transcribes a single file (must already be under Groq's size limit)."""
    print(f"Transcribing {audio_path}...")
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
    if the file exceeds Groq's 25MB upload limit, stitching results
    back together with corrected timestamps.
    """
    file_size = os.path.getsize(audio_path)

    if file_size <= MAX_UPLOAD_BYTES:
        return _transcribe_file(audio_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        chunk_paths = _split_into_chunks(audio_path, CHUNK_DURATION_SEC, tmp_dir)

        combined_text_parts, combined_segments, combined_words = [], [], []
        detected_language = None

        for i, chunk_path in enumerate(chunk_paths):
            offset_sec = i * CHUNK_DURATION_SEC
            result = _transcribe_file(chunk_path)
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
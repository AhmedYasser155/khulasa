"""
pipeline/ingest.py

Stage 1: Ingest.

Migrated from test_whisper_arabic.py's video-to-audio extraction
logic (that script's SOURCE_PATH / VIDEO_EXTENSIONS / resolve_audio_path
mechanism), now parameterized instead of hardcoded.

yt-dlp based YouTube ingestion (ingest_from_youtube) has been tested
standalone via test_yt_dlp_ingest.py and confirmed working.
"""

import os
import re
import subprocess

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

_YOUTUBE_URL_PATTERN = re.compile(
    r"^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)",
    re.IGNORECASE,
)


def is_youtube_url(source: str) -> bool:
    """Used by the orchestrator to decide whether a job's source needs downloading via yt-dlp first."""
    return bool(_YOUTUBE_URL_PATTERN.match(source.strip()))


def extract_audio_from_video(video_path: str) -> str:
    """Pulls just the audio track out of a video file into a standalone mp3."""
    audio_path = os.path.splitext(video_path)[0] + "_extracted_audio.mp3"
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "2",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed:\n{result.stderr[-1500:]}")
    return audio_path


def resolve_audio_path(source_path: str) -> str:
    """Returns a usable audio file path, extracting from video first if needed."""
    ext = os.path.splitext(source_path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return extract_audio_from_video(source_path)
    return source_path


def ingest_from_youtube(url: str, output_dir: str = "tmp") -> str:
    """
    Downloads a YouTube video with yt-dlp, returns local file path.

    Format selector requests best mp4 video + best m4a audio and lets
    yt-dlp merge them via ffmpeg (which is already installed for the
    rest of this pipeline) -- more robust than requiring a single
    pre-merged mp4 stream, since many videos only offer separate
    video/audio streams.

    Tested standalone via test_yt_dlp_ingest.py and confirmed working.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--print", "after_move:filepath",
        "-o", output_template,
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp download failed:\n{result.stderr[-1500:]}")

    downloaded_path = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    if not downloaded_path or not os.path.isfile(downloaded_path):
        raise RuntimeError(f"Could not determine downloaded file path from yt-dlp output:\n{result.stdout}")
    return downloaded_path
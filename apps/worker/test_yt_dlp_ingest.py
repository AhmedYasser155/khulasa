#!/usr/bin/env python3
"""
test_yt_dlp_ingest.py

Standalone test for YouTube ingestion via yt-dlp -- the one pipeline
stage that's never been tested end-to-end until now. Independent of
Groq entirely, so this works regardless of network restrictions on
AI API access.

Setup:
    pip install yt-dlp
    (confirm on PATH: yt-dlp --version)

Usage:
    python test_yt_dlp_ingest.py

Edit TEST_URL below to a short (ideally under 2-3 min) YouTube video
you have rights to test with -- your own content, or something
explicitly Creative Commons licensed, is the safest choice for a
test run.
"""

import os
import subprocess

from app.pipeline import ingest

TEST_URL = "https://www.youtube.com/watch?v=IyX3Pi9gU6M"  # REPLACE_WITH_A_REAL_VIDEO_ID
OUTPUT_DIR = "tmp_ytdlp_test"


def get_video_info(path: str) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,duration,codec_name",
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, text=True,
    )
    info = {}
    for line in result.stdout.strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k] = v
    return info


def main():
    if "REPLACE_WITH_A_REAL_VIDEO_ID" in TEST_URL:
        print("Edit TEST_URL at the top of this script to a real YouTube video first.")
        return

    print(f"Downloading: {TEST_URL}")
    try:
        downloaded_path = ingest.ingest_from_youtube(TEST_URL, output_dir=OUTPUT_DIR)
    except RuntimeError as e:
        print(f"\nDownload FAILED:\n{e}")
        return

    print(f"\nDownloaded to: {downloaded_path}")

    if not os.path.isfile(downloaded_path):
        print("File path returned but file doesn't actually exist -- bug in path parsing.")
        return

    size_mb = os.path.getsize(downloaded_path) / 1024 / 1024
    print(f"File size: {size_mb:.1f} MB")

    print("\nProbing video info...")
    info = get_video_info(downloaded_path)
    for key in ("width", "height", "duration", "codec_name"):
        print(f"  {key}: {info.get(key, 'unknown')}")

    print("\n" + "=" * 60)
    print("Check the file plays correctly (open it), then also confirm:")
    print("  - Resolution/duration look right for the actual video")
    print("  - It has BOTH video and audio (not just one track)")
    print("=" * 60)


if __name__ == "__main__":
    main()  
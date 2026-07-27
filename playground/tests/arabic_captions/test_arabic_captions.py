#!/usr/bin/env python3
"""
test_arabic_captions.py

Standalone test for burning Arabic captions into video, correctly
right-to-left and with properly joined letters.

CONCLUSION FROM TESTING:
- Font (Tajawal) confirmed to have full, valid Arabic glyph coverage
  -- not the problem.
- The generated .srt file was confirmed correct, complete text --
  not the problem either.
- The letter-dropping bug traced specifically to FFmpeg's internal
  SRT-to-ASS conversion step (used when the `subtitles` filter is
  given a .srt file). Writing a native .ass file directly and feeding
  that to the `subtitles` filter bypasses that conversion path
  entirely.
- The earlier "pre-shape the text in Python" approach (arabic_reshaper
  + python-bidi) was tested and rejected separately -- it converts
  letters into Unicode presentation-form codepoints that most modern
  fonts don't have glyphs for. Don't use it.

Setup (Windows PowerShell):

    No extra packages are required.

Uses the transcript from test_whisper_arabic.py
(transcription_result.json) as input -- run that first if you
haven't already.

Usage:

    python test_arabic_captions.py

Edit SOURCE_VIDEO_PATH below to point at your video.
"""

import os
import json
import subprocess

# --- Hardcoded input/output. Change these to test different files. ---
SOURCE_VIDEO_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\zatoona\playground\tests\media\sample_1min_split_screen.mp4"
OUTPUT_VIDEO_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\zatoona\playground\tests\media\sample_1min_with_captions.mp4"
TRANSCRIPT_JSON_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\zatoona\playground\tests\whisper\transcription_result.json"

WORDS_PER_LINE = 4          # how many words per caption line
FONT_NAME = "Arial"


def get_video_resolution(video_path: str) -> tuple[int, int]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=s=x:p=0", video_path],
        capture_output=True, text=True,
    )
    width_str, height_str = result.stdout.strip().split("x")
    return int(width_str), int(height_str)


def seconds_to_ass_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:d}:{minutes:02d}:{secs:05.2f}"


def load_segments(transcript_path: str) -> list[dict]:
    with open(transcript_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("segments", [])


def build_caption_lines(segments: list[dict], words_per_line: int) -> list[dict]:
    """
    Builds caption lines from segment-level text (guaranteed correct
    spelling, since it's Whisper's own natural phrase output) rather
    than reconstructing from word-level tokens. Word-level timestamps
    for Arabic are noticeably less reliable than for space-delimited
    languages -- a single Arabic word can get fragmented into two
    separate "word" tokens, which caused missing/broken letters when
    lines were built by joining word tokens directly.

    Word COUNT (from splitting the segment's own text) is still used
    to split long segments into shorter lines and approximate timing
    proportionally across the segment's start/end -- just not to
    supply the text itself.
    """
    lines = []
    for seg in segments:
        text = seg.get("text", "").strip()
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        seg_duration = seg_end - seg_start

        words = text.split()
        if not words:
            continue
        total = len(words)

        for i in range(0, total, words_per_line):
            chunk = words[i:i + words_per_line]
            frac_start = i / total
            frac_end = min((i + len(chunk)) / total, 1.0)
            lines.append({
                "start": seg_start + frac_start * seg_duration,
                "end": seg_start + frac_end * seg_duration,
                "text": " ".join(chunk),
            })

    return lines


def write_ass(lines: list[dict], path: str, video_width: int, video_height: int):
    """
    Writes a native .ass subtitle file -- bypasses FFmpeg's internal
    SRT-to-ASS conversion step entirely, since that conversion path is
    where the letter-dropping bug was traced to. libass reads this
    format directly and natively.
    """
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT_NAME},{max(16, video_height // 20)},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,{video_height // 20},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for line in lines:
            start = seconds_to_ass_timestamp(line["start"])
            end = seconds_to_ass_timestamp(line["end"])
            f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{line['text']}\n")


def burn_captions(video_path: str, ass_path: str, output_path: str):
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

    vf = f"subtitles={ass_escaped}"

    cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", vf, output_path]
    print(f"\nRunning FFmpeg for {output_path} ...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"FAILED to render {output_path} (see FFmpeg output above)")
    else:
        print(f"Done: {output_path}")


def main():
    if not os.path.isfile(SOURCE_VIDEO_PATH):
        print(f"Video not found: {SOURCE_VIDEO_PATH}")
        return
    if not os.path.isfile(TRANSCRIPT_JSON_PATH):
        print(f"Transcript not found: {TRANSCRIPT_JSON_PATH}. Run test_whisper_arabic.py first.")
        return

    print(f"Using font: {FONT_NAME}")

    segments = load_segments(TRANSCRIPT_JSON_PATH)
    if not segments:
        print("No segments found in transcript JSON.")
        return

    lines = build_caption_lines(segments, WORDS_PER_LINE)
    print(f"Built {len(lines)} caption lines from {len(segments)} segments.")

    video_width, video_height = get_video_resolution(SOURCE_VIDEO_PATH)
    print(f"Video resolution: {video_width}x{video_height}")

    write_ass(lines, "captions.ass", video_width, video_height)
    print("Wrote captions.ass")

    burn_captions(SOURCE_VIDEO_PATH, "captions.ass", OUTPUT_VIDEO_PATH)
    print(f"\nDone. Open {OUTPUT_VIDEO_PATH} to check the result.")


if __name__ == "__main__":
    main()
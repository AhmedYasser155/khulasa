"""
pipeline/captions.py

Stage 5: Arabic caption burn-in.

Migrated from test_arabic_captions.py, carrying forward every fix
found during testing:
  - Captions built from segment-level text, not word-level tokens
    (Arabic word tokens can fragment across two "words", corrupting
    text if reconstructed directly).
  - Native .ass file written directly (bypasses FFmpeg's internal
    SRT-to-ASS conversion path, which was traced as the source of a
    letter-dropping bug).
  - clean_text() strips invisible Unicode "Format" category
    characters (ALM, ZWJ, ZWNJ, etc.) that render as box glyphs in
    virtually any font, regardless of which font is used.
"""

import os
import subprocess
import unicodedata

import requests

FONT_NAME = "Tajawal"
FONT_FILE = "Tajawal-Bold.ttf"
FONT_URL = "https://raw.githubusercontent.com/googlefonts/tajawal/main/fonts/ttf/Tajawal-Bold.ttf"
FONTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fonts"))

WORDS_PER_LINE = 4


def _ensure_font_downloaded() -> str:
    os.makedirs(FONTS_DIR, exist_ok=True)
    font_path = os.path.join(FONTS_DIR, FONT_FILE)
    if os.path.isfile(font_path):
        return font_path
    resp = requests.get(FONT_URL, timeout=30)
    resp.raise_for_status()
    with open(font_path, "wb") as f:
        f.write(resp.content)
    return font_path


def clean_text(text: str) -> str:
    """
    Strips invisible Unicode "Format" category characters. These are
    legitimate direction/joining hints in a full text-editing context,
    but almost no font has an actual visible glyph for them -- when a
    renderer fails to treat them as invisible, they show up as a
    fallback box glyph, regardless of font. Whisper's output can
    include these at certain token boundaries.
    """
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


def _seconds_to_ass_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:d}:{minutes:02d}:{secs:05.2f}"


def _build_caption_lines(segments: list[dict], words_per_line: int) -> list[dict]:
    """
    Builds caption lines from segment-level text (guaranteed correct
    spelling) rather than reconstructing from word-level tokens.
    Word count (from splitting the segment's own text) is used only
    to split long segments into shorter lines and approximate timing
    proportionally -- not to supply the text itself.
    """
    lines = []
    for seg in segments:
        text = clean_text(seg.get("text", "").strip())
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


def _get_video_resolution(video_path: str) -> tuple[int, int]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=s=x:p=0", video_path],
        capture_output=True, text=True,
    )
    width_str, height_str = result.stdout.strip().split("x")
    return int(width_str), int(height_str)


def _write_ass(lines: list[dict], path: str, video_width: int, video_height: int):
    """Native .ass file -- bypasses FFmpeg's SRT-to-ASS conversion path entirely."""
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
            start = _seconds_to_ass_timestamp(line["start"])
            end = _seconds_to_ass_timestamp(line["end"])
            f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{line['text']}\n")


def _filter_and_shift_segments(segments: list[dict], clip_start: float, clip_end: float) -> list[dict]:
    """
    A rendered clip's own video timeline starts at 0:00, but the
    transcript's segment timestamps are absolute (relative to the
    ORIGINAL full-length source video). Without this step, captions
    for any clip that doesn't start at 0:00 in the source would be
    completely out of sync. Keeps only segments overlapping this
    clip's time range, and shifts them so clip_start becomes 0.
    """
    shifted = []
    for seg in segments:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        if seg_end <= clip_start or seg_start >= clip_end:
            continue  # entirely outside this clip's window
        shifted.append({
            **seg,
            "start": max(0.0, seg_start - clip_start),
            "end": min(clip_end, seg_end) - clip_start,
        })
    return shifted


def burn_in_captions(video_path: str, transcript: dict, output_path: str,
                      clip_start: float = 0.0, clip_end: float | None = None) -> str:
    """
    Takes a cropped/reframed clip and the ORIGINAL full transcript,
    burns in Arabic captions, returns the final output path.

    clip_start/clip_end must be the same values used to cut this clip
    in render.py -- they're used to filter the transcript down to just
    this clip's portion and shift timestamps to the clip's own local
    0-based timeline.
    """
    _ensure_font_downloaded()

    segments = transcript.get("segments", [])
    if not segments:
        # No captions to add -- just return the input as-is rather than failing the job.
        return video_path

    if clip_end is None:
        clip_end = max(seg.get("end", 0) for seg in segments)

    clip_segments = _filter_and_shift_segments(segments, clip_start, clip_end)
    if not clip_segments:
        return video_path

    lines = _build_caption_lines(clip_segments, WORDS_PER_LINE)
    video_width, video_height = _get_video_resolution(video_path)

    ass_path = os.path.abspath(os.path.splitext(output_path)[0] + ".ass")
    _write_ass(lines, ass_path, video_width, video_height)

    # FFmpeg's `subtitles` filter has a well-known parsing problem with
    # Windows drive-letter colons (C:) in its argument string -- neither
    # backslash-escaping nor single-quote-wrapping reliably survives it.
    # The reliable fix is to avoid the drive letter entirely by using
    # paths relative to the current working directory instead of
    # absolute paths (this is exactly what the original standalone test
    # script did, which is why it never hit this bug).
    try:
        cwd = os.getcwd()
        ass_arg = os.path.relpath(ass_path, cwd).replace("\\", "/")
        fonts_dir_arg = os.path.relpath(FONTS_DIR, cwd).replace("\\", "/")
    except ValueError:
        # Different drives (e.g. tmp files on D:, process running from C:) --
        # relpath can't bridge that. Fall back to quoted absolute paths.
        ass_arg = ass_path.replace("\\", "/")
        fonts_dir_arg = FONTS_DIR.replace("\\", "/")
        ass_arg, fonts_dir_arg = f"'{ass_arg}'", f"'{fonts_dir_arg}'"

    vf = f"subtitles={ass_arg}:fontsdir={fonts_dir_arg}"

    cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", vf, output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Caption burn-in failed:\n{result.stderr[-1500:]}")

    return output_path
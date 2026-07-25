"""
Stage 5: Arabic caption burn-in.

Correct RTL/contextual shaping matters here — this is the actual
product differentiator vs. English-first competitors. Uses HarfBuzz
for glyph shaping and python-bidi for right-to-left ordering before
generating an .ass subtitle file, then burns it in with FFmpeg's libass filter.
"""


def generate_ass_subtitle(words: list[dict], style: str = "default") -> str:
    """Returns path to a generated .ass subtitle file with correct Arabic shaping."""
    raise NotImplementedError


def burn_in_captions(video_path: str, ass_path: str, output_path: str) -> str:
    """Runs FFmpeg with the libass filter, returns final rendered video path."""
    raise NotImplementedError

"""
pipeline/score.py

Stage 3: Hook scoring.

Migrated from test_llm_hook_scoring.py. The system prompt now lives in
packages/prompts/arabic/hook_scoring.md instead of being hardcoded --
that's the versioned file, so future prompt tuning happens there, not
in this code.
"""

import json
from pathlib import Path

from groq import Groq

MODEL = "llama-3.3-70b-versatile"

# The prompt asks the LLM for 15-90s clips, but that's just a text
# instruction with nothing stopping it from returning something
# outside that range. These constants are the actual enforcement.
MIN_CLIP_DURATION_SEC = 15.0
MAX_CLIP_DURATION_SEC = 90.0

# Adjust this if your actual folder depth differs from the scaffolded structure:
# apps/worker/app/pipeline/score.py -> up 4 levels -> repo root -> packages/prompts/...
PROMPT_PATH = Path(__file__).resolve().parents[4] / "packages" / "prompts" / "arabic" / "hook_scoring.md"


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _format_transcript_for_prompt(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        start, end = seg.get("start", 0), seg.get("end", 0)
        text = seg.get("text", "").strip()
        lines.append(f"[{start:.1f}s - {end:.1f}s] {text}")
    return "\n".join(lines)


def score_clip_candidates(transcript: dict) -> list[dict]:
    """
    Takes the transcript dict returned by transcribe_arabic() and
    returns a ranked list of clip candidates:
    [{"start": float, "end": float, "hook_score": float, "title": str, "reason": str}, ...]
    """
    segments = transcript.get("segments", [])
    if not segments:
        return []

    transcript_text = _format_transcript_for_prompt(segments)
    system_prompt = _load_system_prompt()

    client = Groq()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"النص المفرغ مع التوقيتات:\n\n{transcript_text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    result = json.loads(response.choices[0].message.content)
    candidates = result.get("candidates", [])

    valid_candidates = []
    for c in candidates:
        duration = c.get("end", 0) - c.get("start", 0)
        if MIN_CLIP_DURATION_SEC <= duration <= MAX_CLIP_DURATION_SEC:
            valid_candidates.append(c)
        else:
            print(f"  Dropping candidate outside {MIN_CLIP_DURATION_SEC}-{MAX_CLIP_DURATION_SEC}s "
                  f"range (was {duration:.1f}s): {c.get('title', '')}")

    valid_candidates.sort(key=lambda c: c.get("hook_score", 0), reverse=True)
    return valid_candidates
"""
Stage 3: Hook scoring.

Feeds the transcript to an LLM (prompt lives in packages/prompts/arabic/
hook_scoring.md, not hardcoded here) to find the strongest clip candidates.
"""

PROMPT_PATH = "../../packages/prompts/arabic/hook_scoring.md"


def score_clip_candidates(transcript: dict, dialect: str | None = None) -> list[dict]:
    """
    Returns a list of candidates:
    [{"start": float, "end": float, "hook_score": float, "title": str}, ...]
    """
    raise NotImplementedError("Wire up LLM call using the versioned prompt file.")

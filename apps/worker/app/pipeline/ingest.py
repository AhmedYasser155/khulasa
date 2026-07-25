"""
Stage 1: Ingest.

Pulls source video either from a YouTube URL (via yt-dlp) or from
a direct upload already sitting in R2. Keep this stage dumb — it
should only fetch/validate the source, not touch AI logic.
"""


def ingest_from_youtube(url: str) -> str:
    """Download audio+video via yt-dlp, return local file path."""
    raise NotImplementedError


def ingest_from_upload(r2_object_key: str) -> str:
    """Download an already-uploaded file from R2 to local tmp storage."""
    raise NotImplementedError

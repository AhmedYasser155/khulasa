"""
Stage 2: Transcribe (Arabic).

Swappable ASR provider behind one function signature. Start on
Groq's hosted Whisper large-v3 (cheap/free tier), swap to Deepgram/
ElevenLabs later without touching any other pipeline stage.
"""


def transcribe_arabic(audio_path: str, dialect_hint: str | None = None) -> dict:
    """
    Returns: {
        "segments": [{"start": float, "end": float, "text": str}, ...],
        "words": [{"start": float, "end": float, "word": str}, ...],
        "detected_language": str,
    }
    """
    raise NotImplementedError("Wire up Groq Whisper client here.")

"""
Stage 4: Reframe & cut.

Uses MediaPipe for face detection to compute a smooth vertical (9:16)
crop window, then FFmpeg to cut and render the segment.
"""


def reframe_and_cut(source_path: str, start: float, end: float, output_path: str) -> str:
    """Returns path to the cropped, cut, vertical video (no captions yet)."""
    raise NotImplementedError

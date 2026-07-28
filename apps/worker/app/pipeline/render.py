"""
pipeline/render.py

Stage 4: Reframe & cut.

Merges both tested scripts (test_ffmpeg_reframe.py for single-speaker,
test_ffmpeg_split_screen.py for two-speaker) into one function that
auto-detects which situation applies and picks the right strategy,
instead of you having to choose manually per video.

Uses MediaPipe's Tasks API with the full_range model (short_range
missed a clearly-visible face during testing) and IoU-based
deduplication (duplicate overlapping boxes for the same face were
observed during testing).
"""

import os
import statistics
import subprocess

import cv2
import requests
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

SAMPLE_INTERVAL_SEC = 1.0
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
CELL_HEIGHT = OUTPUT_HEIGHT // 2
ZOOM_FACTOR = 3.5
MIN_DETECTION_CONFIDENCE = 0.2
MIN_SAMPLES_FOR_SPLIT_SCREEN = 5  # need at least this many detections on BOTH sides to treat as two-speaker

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "blaze_face_full_range.tflite")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_detector/"
    "blaze_face_full_range/float16/1/blaze_face_full_range.tflite"
)


def _ensure_model_downloaded():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    if os.path.isfile(MODEL_PATH):
        return
    resp = requests.get(MODEL_URL, timeout=30)
    resp.raise_for_status()
    with open(MODEL_PATH, "wb") as f:
        f.write(resp.content)


def _build_face_detector():
    _ensure_model_downloaded()
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.FaceDetectorOptions(
        base_options=base_options,
        min_detection_confidence=MIN_DETECTION_CONFIDENCE,
    )
    return mp_vision.FaceDetector.create_from_options(options)


def _iou(box_a, box_b) -> float:
    ax1, ay1, aw, ah = box_a
    bx1, by1, bw, bh = box_b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    intersection = iw * ih
    if intersection == 0:
        return 0.0
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0 else 0.0


def _dedupe_detections(detections, iou_threshold: float = 0.3):
    if not detections:
        return []
    sorted_dets = sorted(
        detections,
        key=lambda d: d.categories[0].score if d.categories else 0.0,
        reverse=True,
    )
    kept = []
    for det in sorted_dets:
        box = det.bounding_box
        box_tuple = (box.origin_x, box.origin_y, box.width, box.height)
        is_duplicate = any(
            _iou(box_tuple, (k.bounding_box.origin_x, k.bounding_box.origin_y,
                              k.bounding_box.width, k.bounding_box.height)) > iou_threshold
            for k in kept
        )
        if not is_duplicate:
            kept.append(det)
    return kept


def _detect_faces_by_side(video_path: str, start: float, end: float):
    """
    Samples frames in [start, end], detects faces, splits into
    left/right clusters by frame midpoint. Returns:
        (left_faces, right_faces, frame_width, frame_height)
    where each faces list is a list of (cx, cy, w, h) tuples.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    midpoint = frame_width / 2

    start_frame = int(start * fps)
    end_frame = int(end * fps)
    frame_interval = max(1, int(fps * SAMPLE_INTERVAL_SEC))

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    detector = _build_face_detector()

    left_faces, right_faces = [], []
    frame_idx = start_frame

    while frame_idx < end_frame:
        ret, frame = cap.read()
        if not ret:
            break

        if (frame_idx - start_frame) % frame_interval == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_image)
            detections = _dedupe_detections(result.detections) if result.detections else []

            for det in detections:
                box = det.bounding_box
                cx = box.origin_x + box.width / 2
                cy = box.origin_y + box.height / 2
                if cx < midpoint:
                    left_faces.append((cx, cy, box.width, box.height))
                else:
                    right_faces.append((cx, cy, box.width, box.height))

        frame_idx += 1

    cap.release()
    detector.close()
    return left_faces, right_faces, frame_width, frame_height


def _compute_crop_box(faces, frame_width, frame_height, cell_aspect_wh, zoom_factor=ZOOM_FACTOR):
    if faces:
        median_x = statistics.median(f[0] for f in faces)
        median_y = statistics.median(f[1] for f in faces)
        median_face_h = statistics.median(f[3] for f in faces)
    else:
        median_x = frame_width / 2
        median_y = frame_height / 2
        median_face_h = frame_height / 4

    crop_height = min(frame_height, median_face_h * zoom_factor)
    crop_width = crop_height * cell_aspect_wh

    if crop_width > frame_width:
        crop_width = frame_width
        crop_height = crop_width / cell_aspect_wh

    crop_width, crop_height = int(crop_width), int(crop_height)
    x_offset = int(median_x - crop_width / 2)
    y_offset = int(median_y - crop_height * 0.4)
    x_offset = max(0, min(x_offset, frame_width - crop_width))
    y_offset = max(0, min(y_offset, frame_height - crop_height))
    return crop_width, crop_height, x_offset, y_offset


def _render_single(video_path, start, end, output_path, crop_box):
    w, h, x, y = crop_box
    vf = f"crop={w}:{h}:{x}:{y},scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}"
    cmd = ["ffmpeg", "-y", "-i", video_path, "-ss", str(start), "-to", str(end),
           "-vf", vf, "-c:a", "aac", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg single-crop render failed:\n{result.stderr[-1500:]}")


def _render_split_screen(video_path, start, end, output_path, top_box, bottom_box):
    tw, th, tx, ty = top_box
    bw, bh, bx, by = bottom_box
    filter_complex = (
        f"[0:v]crop={tw}:{th}:{tx}:{ty},scale={OUTPUT_WIDTH}:{CELL_HEIGHT}[top];"
        f"[0:v]crop={bw}:{bh}:{bx}:{by},scale={OUTPUT_WIDTH}:{CELL_HEIGHT}[bottom];"
        f"[top][bottom]vstack=inputs=2[v]"
    )
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-ss", str(start), "-to", str(end),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "0:a?", "-c:a", "aac",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg split-screen render failed:\n{result.stderr[-1500:]}")


def reframe_and_cut(video_path: str, start: float, end: float, output_path: str) -> str:
    """
    Cuts [start, end] out of video_path and reframes it to 9:16.
    Auto-detects single vs. two-speaker layout based on face
    detection results and picks the matching render strategy.
    """
    left_faces, right_faces, frame_width, frame_height = _detect_faces_by_side(video_path, start, end)

    is_split_screen = (
        len(left_faces) >= MIN_SAMPLES_FOR_SPLIT_SCREEN
        and len(right_faces) >= MIN_SAMPLES_FOR_SPLIT_SCREEN
    )

    if is_split_screen:
        cell_aspect = OUTPUT_WIDTH / CELL_HEIGHT
        top_box = _compute_crop_box(left_faces, frame_width, frame_height, cell_aspect)
        bottom_box = _compute_crop_box(right_faces, frame_width, frame_height, cell_aspect)
        _render_split_screen(video_path, start, end, output_path, top_box, bottom_box)
    else:
        all_faces = left_faces + right_faces
        full_aspect = OUTPUT_WIDTH / OUTPUT_HEIGHT
        crop_box = _compute_crop_box(all_faces, frame_width, frame_height, full_aspect)
        _render_single(video_path, start, end, output_path, crop_box)

    return output_path
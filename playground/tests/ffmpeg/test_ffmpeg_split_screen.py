#!/usr/bin/env python3
"""
test_ffmpeg_split_screen.py

Standalone test: detect TWO speakers' face positions (assumes a
side-by-side recording layout, e.g. two webcam feeds or a two-camera
podcast setup), compute a vertical crop window per speaker, then use
FFmpeg to stack them into a single 9:16 split-screen vertical video
(speaker A on top, speaker B on bottom).

Same "one averaged window for the whole clip" simplification as the
single-speaker version -- proves the split-screen mechanism works
before adding per-segment dynamic tracking.

Clustering approach: for each sampled frame, faces left of the frame's
horizontal midpoint are assigned to "left speaker", faces right of it
to "right speaker". This is a simple, reliable heuristic for standard
side-by-side recordings -- it will NOT work well if both speakers
share the same half of the frame (e.g. sitting close together in one
camera shot). That's a known limitation, not a bug.

Setup (Windows PowerShell):

    winget install ffmpeg
    pip install opencv-python-headless mediapipe requests

Usage:

    python test_ffmpeg_split_screen.py

Edit SOURCE_VIDEO_PATH below to point at your file.
"""

import os
import subprocess
import statistics

import cv2
import requests
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# --- Hardcoded input/output. Change these to test different files. ---
SOURCE_VIDEO_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\zatoona\playground\tests\media\sample_1min.mp4"
OUTPUT_VIDEO_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\zatoona\playground\tests\media\sample_1min_split_screen.mp4"

SAMPLE_INTERVAL_SEC = 1.0
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920            # full stacked output is 9:16
CELL_HEIGHT = OUTPUT_HEIGHT // 2  # each speaker's half
ZOOM_FACTOR = 3.5                # higher = tighter/closer crop around each face

MODEL_PATH = "blaze_face_full_range.tflite"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_detector/"
    "blaze_face_full_range/float16/1/blaze_face_full_range.tflite"
)
MIN_DETECTION_CONFIDENCE = 0.2


def ensure_model_downloaded():
    if os.path.isfile(MODEL_PATH):
        return
    print("Downloading face detection model (one-time)...")
    resp = requests.get(MODEL_URL, timeout=30)
    resp.raise_for_status()
    with open(MODEL_PATH, "wb") as f:
        f.write(resp.content)
    print(f"Saved model to {MODEL_PATH}")


def build_face_detector():
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.FaceDetectorOptions(
        base_options=base_options,
        min_detection_confidence=MIN_DETECTION_CONFIDENCE,
    )
    return mp_vision.FaceDetector.create_from_options(options)


def _iou(box_a, box_b) -> float:
    """Intersection-over-union of two (x, y, w, h) boxes."""
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


def dedupe_detections(detections, iou_threshold: float = 0.3):
    """
    Merges overlapping duplicate detections of the same face, keeping
    only the highest-confidence box per cluster.
    """
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


def detect_two_speaker_centers(video_path: str, sample_interval_sec: float):
    """
    Samples frames, detects all faces per frame, and splits them into
    "left speaker" / "right speaker" clusters based on which half of
    the frame each face falls in. Returns:
        (left_faces, right_faces, frame_width, frame_height)
    where each faces list is a list of (cx_px, cy_px, w_px, h_px) tuples
    -- center position AND size of each detected face box.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_interval = max(1, int(fps * sample_interval_sec))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    midpoint = frame_width / 2

    detector = build_face_detector()

    left_faces = []
    right_faces = []
    frame_idx = 0
    checked = 0
    frames_with_two_faces = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            checked += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_image)
            detections = dedupe_detections(result.detections) if result.detections else []

            if detections:
                if len(detections) >= 2:
                    frames_with_two_faces += 1
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
    print(f"Sampled {checked} frames; frames with 2+ faces detected: {frames_with_two_faces}")
    print(f"Left-cluster samples: {len(left_faces)}, Right-cluster samples: {len(right_faces)}")
    return left_faces, right_faces, frame_width, frame_height


def compute_crop_box(faces, frame_width, frame_height, cell_aspect_wh, zoom_factor=3.5):
    """
    Generic crop-box computation for one speaker, based on FACE SIZE
    (not full frame height) so it actually zooms in around the person
    instead of barely trimming the frame edges. zoom_factor controls
    how much room is left around the face (headshot + shoulders/chest).
    """
    if faces:
        median_x = statistics.median(f[0] for f in faces)
        median_y = statistics.median(f[1] for f in faces)
        median_face_h = statistics.median(f[3] for f in faces)
    else:
        median_x = frame_width / 2
        median_y = frame_height / 2
        median_face_h = frame_height / 4   # reasonable fallback guess

    crop_height = min(frame_height, median_face_h * zoom_factor)
    crop_width = crop_height * cell_aspect_wh

    if crop_width > frame_width:
        crop_width = frame_width
        crop_height = crop_width / cell_aspect_wh

    crop_width = int(crop_width)
    crop_height = int(crop_height)

    x_offset = int(median_x - crop_width / 2)
    # Bias the vertical framing so the face sits in the upper-middle of
    # the crop (room below for shoulders/chest), not dead-center.
    y_offset = int(median_y - crop_height * 0.4)

    x_offset = max(0, min(x_offset, frame_width - crop_width))
    y_offset = max(0, min(y_offset, frame_height - crop_height))

    return crop_width, crop_height, x_offset, y_offset


def render_split_screen(video_path: str, output_path: str, left_box, right_box):
    lw, lh, lx, ly = left_box
    rw, rh, rx, ry = right_box

    filter_complex = (
        f"[0:v]crop={lw}:{lh}:{lx}:{ly},scale={OUTPUT_WIDTH}:{CELL_HEIGHT}[top];"
        f"[0:v]crop={rw}:{rh}:{rx}:{ry},scale={OUTPUT_WIDTH}:{CELL_HEIGHT}[bottom];"
        f"[top][bottom]vstack=inputs=2[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",       # keep original audio if present, don't fail if not
        "-c:a", "copy",
        output_path,
    ]
    print("\nRunning FFmpeg (progress will print live below)...")
    print(" ".join(cmd))
    result = subprocess.run(cmd)   # no capture_output -- lets FFmpeg's progress stream to console

    if result.returncode != 0:
        print("\nFFmpeg FAILED (see output above)")
    else:
        print(f"\nDone. Split-screen vertical clip saved to: {output_path}")


def main():
    ensure_model_downloaded()

    print(f"\nAnalyzing: {SOURCE_VIDEO_PATH}\n")
    left_faces, right_faces, width, height = detect_two_speaker_centers(
        SOURCE_VIDEO_PATH, SAMPLE_INTERVAL_SEC
    )

    if not left_faces:
        print("WARNING: no faces detected on the left half -- top cell will be dead-center.")
    if not right_faces:
        print("WARNING: no faces detected on the right half -- bottom cell will be dead-center.")

    cell_aspect = OUTPUT_WIDTH / CELL_HEIGHT
    left_box = compute_crop_box(left_faces, width, height, cell_aspect, ZOOM_FACTOR)
    right_box = compute_crop_box(right_faces, width, height, cell_aspect, ZOOM_FACTOR)

    print(f"Top cell crop box (w,h,x,y): {left_box}")
    print(f"Bottom cell crop box (w,h,x,y): {right_box}")

    render_split_screen(SOURCE_VIDEO_PATH, OUTPUT_VIDEO_PATH, left_box, right_box)


if __name__ == "__main__":
    main()
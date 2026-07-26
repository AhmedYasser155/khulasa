#!/usr/bin/env python3
"""
diagnose_face_detection.py

Diagnostic tool: samples a handful of frames evenly across the video,
runs face detection on each, and saves annotated JPGs with the
detected bounding boxes (and the left/right midline) drawn on them --
so you can SEE what the detector found instead of guessing from
numbers alone.

Setup:
    pip install opencv-python-headless mediapipe requests

Usage:
    python diagnose_face_detection.py

Edit SOURCE_VIDEO_PATH and NUM_SAMPLE_FRAMES below.
Output frames are saved to a folder called diagnostic_frames/.
"""

import os
import cv2
import requests
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

SOURCE_VIDEO_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\khulasa\playground\tests\media\sample.mp4"

NUM_SAMPLE_FRAMES = 12          # spread evenly across the whole video
MIN_DETECTION_CONFIDENCE = 0.2  # lowered further for this diagnostic
OUTPUT_DIR = "diagnostic_frames"

# full_range model: better for faces further from camera / medium-distance
# multi-person shots than the short_range model we started with.
MODEL_PATH = "blaze_face_full_range.tflite"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_detector/"
    "blaze_face_full_range/float16/1/blaze_face_full_range.tflite"
)


def ensure_model_downloaded():
    if os.path.isfile(MODEL_PATH):
        return
    print("Downloading face detection model (one-time)...")
    resp = requests.get(MODEL_URL, timeout=30)
    resp.raise_for_status()
    with open(MODEL_PATH, "wb") as f:
        f.write(resp.content)


def build_face_detector(min_confidence: float):
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.FaceDetectorOptions(
        base_options=base_options,
        min_detection_confidence=min_confidence,
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
    only the highest-confidence box per cluster. Prevents one real
    face from being counted/drawn twice.
    """
    if not detections:
        return []

    # Sort by confidence, highest first
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


def main():
    ensure_model_downloaded()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cap = cv2.VideoCapture(SOURCE_VIDEO_PATH)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {SOURCE_VIDEO_PATH}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video: {width}x{height}, {total_frames} total frames")

    sample_indices = [
        int(total_frames * i / (NUM_SAMPLE_FRAMES + 1))
        for i in range(1, NUM_SAMPLE_FRAMES + 1)
    ]

    detector = build_face_detector(MIN_DETECTION_CONFIDENCE)
    midpoint = width // 2

    for i, frame_idx in enumerate(sample_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            print(f"  [{i}] could not read frame {frame_idx}")
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_image)
        detections = dedupe_detections(result.detections) if result.detections else []

        # draw the left/right midline
        cv2.line(frame, (midpoint, 0), (midpoint, height), (0, 255, 255), 2)

        num_faces = len(detections)
        print(f"  [{i}] frame {frame_idx}: {num_faces} face(s) detected (after de-dup)")

        if detections:
            for det in detections:
                box = det.bounding_box
                x, y, w, h = box.origin_x, box.origin_y, box.width, box.height
                score = det.categories[0].score if det.categories else 0.0
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                cx = x + w // 2
                label = f"{score:.2f} cx={cx}"
                cv2.putText(frame, label, (x, max(0, y - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        out_path = os.path.join(OUTPUT_DIR, f"frame_{i:02d}_idx{frame_idx}.jpg")
        cv2.imwrite(out_path, frame)

    cap.release()
    detector.close()
    print(f"\nSaved {len(sample_indices)} annotated frames to ./{OUTPUT_DIR}/")
    print("Open a few of these images and look at:")
    print("  1. Is the yellow midline actually where the two camera feeds meet?")
    print("  2. Are faces present but NOT boxed (detector missing them)?")
    print("  3. Are faces boxed only on one side even though both people are visible?")


if __name__ == "__main__":
    main()
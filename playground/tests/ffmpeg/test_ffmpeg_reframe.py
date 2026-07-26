#!/usr/bin/env python3
"""
test_ffmpeg_reframe.py

Standalone test: detect the speaker's face position using MediaPipe's
Tasks API (the current, maintained API -- the older mp.solutions API
is broken/missing on many recent pip installs), compute a smart 9:16
vertical crop window centered on them, then use FFmpeg to cut and
render the vertical clip.

This is the "simple version": one averaged crop window for the whole
clip, not frame-by-frame dynamic tracking. Proves MediaPipe detection
+ FFmpeg cropping both work, before adding the complexity of a
moving/dynamic crop.

Setup (Windows PowerShell):

    winget install ffmpeg
    (close/reopen terminal, confirm with: ffmpeg -version)
    pip install opencv-python-headless mediapipe requests

The face detection model (~a few hundred KB) is downloaded
automatically on first run and cached locally.

Usage:

    python test_ffmpeg_reframe.py

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
#C:\Users\aayasser\Desktop\PLAYGROUND\khulasa\playground\tests\ffmpeg\video_3000.mp4
SOURCE_VIDEO_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\khulasa\playground\tests\ffmpeg\video_3000.mp4"
OUTPUT_VIDEO_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\khulasa\playground\tests\ffmpeg\video_3000_vertical.mp4"

SAMPLE_INTERVAL_SEC = 1.0     # check for a face roughly once per second
TARGET_ASPECT = 9 / 16        # width:height for the output

MODEL_PATH = "blaze_face_short_range.tflite"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_detector/"
    "blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
)


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
    options = mp_vision.FaceDetectorOptions(base_options=base_options)
    return mp_vision.FaceDetector.create_from_options(options)


def detect_face_centers_px(video_path: str, sample_interval_sec: float) -> list[float]:
    """
    Samples frames at a fixed interval, runs face detection on each,
    and returns a list of horizontal face-center positions IN PIXELS
    -- one per frame where a face was found.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_interval = max(1, int(fps * sample_interval_sec))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    detector = build_face_detector()

    centers_px = []
    frame_idx = 0
    checked = 0
    found = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            checked += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_image)

            if result.detections:
                found += 1
                box = result.detections[0].bounding_box  # pixel coords, not normalized
                center_x_px = box.origin_x + box.width / 2
                centers_px.append(center_x_px)

        frame_idx += 1

    cap.release()
    detector.close()
    print(f"Sampled {checked} frames out of {total_frames}, face found in {found}")
    return centers_px


def compute_crop_window(video_path: str, centers_px: list[float]) -> tuple[int, int, int, int]:
    """
    Returns (crop_width, crop_height, x_offset, y_offset) in pixels
    for a 9:16 crop centered on the median detected face position.
    Falls back to dead-center if no face was ever detected.
    """
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    crop_height = height
    crop_width = int(crop_height * TARGET_ASPECT)

    if crop_width > width:
        # Source isn't wide enough for a full-height 9:16 crop --
        # fall back to full width and crop height instead.
        crop_width = width
        crop_height = int(crop_width / TARGET_ASPECT)

    if centers_px:
        center_x_px = statistics.median(centers_px)
        print(f"Median face center: {center_x_px:.0f}px (frame width {width}px)")
    else:
        center_x_px = width / 2
        print("No face detected in any sampled frame -- falling back to dead-center crop.")

    x_offset = int(center_x_px - crop_width / 2)
    # Clamp so the crop window stays fully inside the frame
    x_offset = max(0, min(x_offset, width - crop_width))
    y_offset = max(0, (height - crop_height) // 2)

    return crop_width, crop_height, x_offset, y_offset


def render_vertical_crop(video_path: str, output_path: str, crop_box: tuple[int, int, int, int]):
    crop_width, crop_height, x_offset, y_offset = crop_box
    crop_filter = f"crop={crop_width}:{crop_height}:{x_offset}:{y_offset}"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", crop_filter,
        "-c:a", "copy",
        output_path,
    ]
    print("\nRunning FFmpeg:")
    print(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("\nFFmpeg FAILED:")
        print(result.stderr[-2000:])   # last chunk of stderr is usually the useful part
    else:
        print(f"\nDone. Vertical clip saved to: {output_path}")


def main():
    ensure_model_downloaded()

    print(f"\nAnalyzing: {SOURCE_VIDEO_PATH}\n")
    centers_px = detect_face_centers_px(SOURCE_VIDEO_PATH, SAMPLE_INTERVAL_SEC)
    crop_box = compute_crop_window(SOURCE_VIDEO_PATH, centers_px)
    print(f"Crop window (w, h, x, y): {crop_box}")
    render_vertical_crop(SOURCE_VIDEO_PATH, OUTPUT_VIDEO_PATH, crop_box)


if __name__ == "__main__":
    main()
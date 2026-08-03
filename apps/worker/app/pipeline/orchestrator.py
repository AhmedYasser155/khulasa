"""
pipeline/orchestrator.py

Ties every tested pipeline stage together into one job run.
This is the only genuinely new piece -- everything it calls is
migrated, tested logic from the standalone scripts.
"""

import os
import uuid

from app.core import jobs, storage
from app.pipeline import ingest, transcribe, refine_transcript, score, render, captions

TMP_DIR = "tmp"


def run_pipeline(job_id: str, source_path: str):
    """
    source_path can be:
      - a local file path (video or audio) -- used directly
      - an R2 object key, prefixed "r2://" -- downloaded first via storage.download_to_local
      - a YouTube URL -- downloaded first via ingest.ingest_from_youtube
    """
    try:
        os.makedirs(TMP_DIR, exist_ok=True)

        jobs.update_job(job_id, status="ingesting")
        if source_path.startswith("r2://"):
            key = source_path.replace("r2://", "")
            local_path = os.path.join(TMP_DIR, os.path.basename(key))
            storage.download_to_local(key, local_path)
        elif ingest.is_youtube_url(source_path):
            local_path = ingest.ingest_from_youtube(source_path, output_dir=TMP_DIR)
        else:
            local_path = source_path

        jobs.update_job(job_id, status="transcribing")
        audio_path = ingest.resolve_audio_path(local_path)
        transcript = transcribe.transcribe_arabic(audio_path)

        jobs.update_job(job_id, status="refining")
        # verify_quran=True -- validated against 15 test cases (full quotes,
        # partial quotes, a repeated-refrain stress test, and a negative
        # case) in test_quran_reference.py before enabling this.
        transcript = refine_transcript.refine_transcript(transcript, verify_quran=True)

        jobs.update_job(job_id, status="scoring")
        candidates = score.score_clip_candidates(transcript)
        if not candidates:
            jobs.update_job(job_id, status="failed", error="No clip candidates found")
            return

        jobs.update_job(job_id, status="rendering")
        clip_urls = []

        for i, candidate in enumerate(candidates):
            clip_start = candidate["start"]
            clip_end = candidate["end"]

            cropped_path = os.path.join(TMP_DIR, f"{job_id}_clip{i}_cropped.mp4")
            render.reframe_and_cut(local_path, clip_start, clip_end, cropped_path)

            captioned_path = os.path.join(TMP_DIR, f"{job_id}_clip{i}_final.mp4")
            captions.burn_in_captions(
                cropped_path, transcript, captioned_path,
                clip_start=clip_start, clip_end=clip_end,
            )

            jobs.update_job(job_id, status="uploading")
            object_key = f"clips/{job_id}/clip_{i}.mp4"
            storage.upload_local_file(captioned_path, object_key)
            download_url = storage.generate_presigned_download_url(object_key)

            clip_urls.append({
                "url": download_url,
                "title": candidate.get("title", ""),
                "hook_score": candidate.get("hook_score", 0),
                "start": clip_start,
                "end": clip_end,
            })

        jobs.update_job(job_id, status="done", clip_urls=clip_urls)

    except Exception as e:
        jobs.update_job(job_id, status="failed", error=str(e))
        raise
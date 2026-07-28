#!/usr/bin/env python3
"""
test_r2_upload.py

Standalone test for the presigned-upload flow against Cloudflare R2.
Proves the pattern the whole product depends on: server generates a
temporary upload URL, "client" uploads directly to storage, server
never touches the file bytes.

Setup (Windows PowerShell):

    pip install boto3 requests python-dotenv

Add to your .env (same folder as this script, or project root):

    R2_ACCOUNT_ID=your_account_id
    R2_ACCESS_KEY_ID=your_access_key_id
    R2_SECRET_ACCESS_KEY=your_secret_access_key
    R2_BUCKET_NAME=khulasa-media

Usage:

    python test_r2_upload.py

Edit TEST_FILE_PATH below to point at any file you want to test with
(a small video or even a .txt file is fine for this test).
"""

import os
import boto3
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Hardcoded input. Change this to test a different file. ---
TEST_FILE_PATH = r"E:\FFOutput\1.mp3"
OBJECT_KEY = "test-uploads2/1.mp3"   # where it will land inside the bucket

ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID")
SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
BUCKET_NAME = os.environ.get("R2_BUCKET_NAME")


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="auto",   # R2 ignores region but boto3 requires the param
    )


def generate_presigned_upload_url(client, key: str, expires_in: int = 3600) -> str:
    """This is the function your API's /upload-url endpoint would call."""
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )


def generate_presigned_download_url(client, key: str, expires_in: int = 3600) -> str:
    """This is what you'd hand back to the client once a clip is ready."""
    return client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )


def main():
    missing = [name for name, val in [
        ("R2_ACCOUNT_ID", ACCOUNT_ID),
        ("R2_ACCESS_KEY_ID", ACCESS_KEY),
        ("R2_SECRET_ACCESS_KEY", SECRET_KEY),
        ("R2_BUCKET_NAME", BUCKET_NAME),
    ] if not val]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}. Check your .env file.")
        return

    if not os.path.isfile(TEST_FILE_PATH):
        print(f"File not found: {TEST_FILE_PATH}")
        return

    client = get_r2_client()

    # --- Step 1: server generates a presigned UPLOAD url ---
    upload_url = generate_presigned_upload_url(client, OBJECT_KEY)
    print("Presigned UPLOAD URL generated (expires in 1 hour):")
    print(upload_url)
    print()

    # --- Step 2: "client" uploads directly to R2 using that URL ---
    # In a real app, this happens in the browser via fetch()/XHR PUT,
    # not in your backend. We simulate it here with `requests` to prove
    # the URL itself actually works end to end.
    print(f"Uploading {TEST_FILE_PATH} directly to R2 (simulating client)...")
    with open(TEST_FILE_PATH, "rb") as f:
        resp = requests.put(upload_url, data=f)

    if resp.status_code == 200:
        print(f"Upload succeeded (HTTP {resp.status_code})")
    else:
        print(f"Upload FAILED (HTTP {resp.status_code}): {resp.text}")
        return

    # --- Step 3: confirm the object actually landed in the bucket ---
    head = client.head_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
    print(f"\nConfirmed in bucket: {OBJECT_KEY}")
    print(f"  Size: {head['ContentLength']} bytes")
    print(f"  Last modified: {head['LastModified']}")

    # --- Step 4: generate a presigned DOWNLOAD url (what you'd send a user) ---
    download_url = generate_presigned_download_url(client, OBJECT_KEY)
    print("\nPresigned DOWNLOAD URL (share this, or open it in a browser):")
    print(download_url)


if __name__ == "__main__":
    main()
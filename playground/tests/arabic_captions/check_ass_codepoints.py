#!/usr/bin/env python3
"""
check_ass_codepoints.py

Diagnostic: prints the exact Unicode codepoint of every character in
any caption line containing "لا" or "لأ", so we can identify exactly
which invisible character is showing up as a box before the ligature,
instead of guessing.

Usage:
    python check_ass_codepoints.py
"""

import re

import unicodedata

ASS_PATH = "captions.ass"


def char_name(ch: str) -> str:
    try:
        return unicodedata.name(ch)
    except ValueError:
        return "(no name -- likely a control/formatting character)"


def main():
    with open(ASS_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    dialogue_lines = [l for l in lines if l.startswith("Dialogue:")]
    target_lines = [l for l in dialogue_lines if "لا" in l or "لأ" in l]

    if not target_lines:
        print("No dialogue lines containing 'لا' or 'لأ' found.")
        return

    print(f"Found {len(target_lines)} matching line(s). Showing first 3:\n")

    for line in target_lines[:3]:
        # Extract just the text portion (after the 9th comma, per ASS Dialogue format)
        parts = line.strip().split(",", 9)
        text = parts[9] if len(parts) > 9 else line.strip()

        print("=" * 60)
        print(f"Full text: {text}")
        print("-" * 60)
        print("Character-by-character breakdown:")
        for ch in text:
            print(f"  {ch!r}  U+{ord(ch):04X}  {char_name(ch)}")
        print()


if __name__ == "__main__":
    main()
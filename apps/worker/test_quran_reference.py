#!/usr/bin/env python3
"""
test_quran_reference.py

Standalone test for the Quran matching module. Includes full-ayah
quotes, PARTIAL (mid-ayah) quotes, a repeated-refrain stress test, and
a deliberate negative case (a religious-sounding phrase that is NOT
actual Quran text) -- verify all of this before trusting the matcher
inside a real job.

Some phrases are worded identically in more than one place in the
Quran (e.g. the Ar-Rahman refrain, or the closing phrase shared by
2:255 and 42:4). For those, "expected" is a LIST of acceptable
(surah, ayah) answers -- any one of them is a correct citation, since
the matcher can't (and shouldn't try to) guess which specific
occurrence was intended from the phrase alone.

Usage:
    python test_quran_reference.py
"""

import json

from app.pipeline import quran_reference as qr

# Each case: (input_text, expected, note)
# expected = None            -> no confident match expected (negative/too-ambiguous case)
# expected = [(surah, ayah)] -> exactly one correct answer
# expected = [(s1,a1), (s2,a2), ...] -> any of these is a correct citation
TEST_CASES = [
    # --- Full-ayah quotes (baseline) ---
    ("قل اعوذ برب الفلق", [(113, 1)], "full ayah"),
    ("من شر ما خلق", [(113, 2)], "full ayah"),
    ("قل اعوذ برب الناس", [(114, 1)], "full ayah"),
    ("من شر الوسواس الخناس", [(114, 4)], "full ayah"),
    ("بسم الله الرحمن الرحيم", None, "Basmalah -- may or may not be separately indexed"),

    # --- Partial / mid-ayah quotes ---
    ("من شر الوسواس", [(114, 4)], "PARTIAL -- cut before 'الخناس'"),
    ("الذي يوسوس في صدور", [(114, 5)], "PARTIAL -- cut before 'الناس'"),
    ("له ما في السماوات وما في الارض",
     [(2, 255), (42, 4)],
     "PARTIAL -- this exact phrase appears identically in both 2:255 and 42:4; either is a correct citation"),
    ("ولم يكن له كفوا", [(112, 4)], "PARTIAL -- cut before 'احد'"),
    ("وهو العلي العظيم",
     [(2, 255), (42, 4)],
     "PARTIAL -- closing phrase shared identically by 2:255 and 42:4; either is a correct citation"),

    # --- Other complex cases ---
    ("الله الصمد", [(112, 2)], "short full ayah"),
    ("لم يلد ولم يولد", [(112, 3)], "wasla-alif normalization check (ٱ in dataset)"),
    ("فبأي الاء ربكما تكذبان", None,
     "REPEATED REFRAIN -- appears ~31x in Ar-Rahman (55), ayah number is genuinely ambiguous by design"),
    ("الرحمن الرحيم", None, "very short, likely ambiguous/ties with many ayat"),
    ("الحمد لله على كل حال", None, "NEGATIVE CASE -- common phrase, NOT actual Quran wording"),
]


def main():
    print("Loading dataset...")
    ayat = qr._load_ayat()
    print(f"Loaded {len(ayat)} ayat total.\n")

    results = []
    correct = 0
    scored_cases = 0

    for candidate_text, expected, note in TEST_CASES:
        match = qr.find_matching_ayah(candidate_text)

        entry = {
            "input": candidate_text,
            "note": note,
            "expected": expected,
            "match": None,
            "status": None,
        }

        print(f"\nInput:    {candidate_text}")
        print(f"Note:     {note}")

        if match:
            entry["match"] = {
                "surah_id": match["surah_id"],
                "surah_name": match["surah_name"],
                "ayah_id": match["ayah_id"],
                "text": match["text"],
                "score": round(match["score"], 4),
            }
            print(f"Match:    {match['text']}")
            print(f"Location: Surah {match['surah_id']} ({match['surah_name']}), Ayah {match['ayah_id']}")
            print(f"Score:    {match['score']:.3f}")

            if expected is None:
                entry["status"] = "matched (expected none/ambiguous)"
                print("Expected: none/ambiguous -- got a match, review manually")
            else:
                scored_cases += 1
                is_correct = any(
                    match["surah_id"] == s and match["ayah_id"] == a
                    for s, a in expected
                )
                entry["status"] = "CORRECT" if is_correct else "WRONG"
                correct += is_correct
                expected_str = " or ".join(f"Surah {s}:{a}" for s, a in expected)
                print(f"Expected: {expected_str} -- {entry['status']}")
        else:
            entry["status"] = "no match"
            print("Match:    (none found above threshold)")
            if expected is not None:
                scored_cases += 1
                entry["status"] = "MISSED"
                expected_str = " or ".join(f"Surah {s}:{a}" for s, a in expected)
                print(f"Expected: {expected_str} -- MISSED")
            else:
                print("Expected: none -- correctly found nothing")

        results.append(entry)

    print("\n" + "=" * 70)
    print(f"Correct matches (scored cases only): {correct}/{scored_cases}")
    print("=" * 70)

    out_path = "quran_reference_test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_ayat_loaded": len(ayat),
            "correct": correct,
            "scored_cases": scored_cases,
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nFull results saved to {out_path}")
    print("\nRead every WRONG, MISSED, and 'matched (expected none/ambiguous)' entry")
    print("by eye before enabling verify_quran=True in the real pipeline.")


if __name__ == "__main__":
    main()
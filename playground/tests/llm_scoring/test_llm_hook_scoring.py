#!/usr/bin/env python3
"""
test_llm_hook_scoring.py

Standalone test for the "hook scoring" stage: feeds an Arabic
transcript (with timestamps) to an LLM via Groq and asks it to find
the strongest short-clip candidates.

Reuses the output of test_whisper_arabic.py (transcription_result.json)
as input -- run that script first if you haven't already.

Setup (Windows PowerShell):

    pip install groq python-dotenv
    (GROQ_API_KEY should already be set from the Whisper test)

Usage:

    python test_llm_hook_scoring.py

Edit TRANSCRIPT_JSON_PATH below if your file is somewhere else.
"""

import os
import json

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- Hardcoded input. Change this to point at a different transcript. ---
TRANSCRIPT_JSON_PATH = r"C:\Users\aayasser\Desktop\PLAYGROUND\khulasa\playground\tests\whisper\transcription_result.json"

# llama-3.3-70b-versatile is Groq's strong general-purpose free-tier model.
# Worth also trying "allam-2-7b-instruct" (SDAIA's Arabic-specialized model,
# also free on Groq) as a comparison -- swap MODEL below to test that.
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """أنت خبير في تحليل النصوص المفرغة من الفيديوهات العربية لاختيار
أفضل المقاطع القصيرة القابلة للانتشار (15-90 ثانية لكل مقطع).

ابحث عن لحظات فيها:
- بداية قوية تجذب المشاهد خلال أول ثانيتين
- ذروة عاطفية، كشف مفاجئ، أو جملة تستحق الاقتباس
- نقطة بداية ونهاية طبيعية (لا تحتاج سياق سابق لفهمها)
- طرافة أو إثارة جدل أو فائدة عملية واضحة

انتبه للهجة وسياق الفيديو: أفضل لحظة في محاضرة دينية تختلف عن أفضل لحظة
في مقطع كوميدي. احترم نبرة المحتوى الأصلي.

أعد النتيجة بصيغة JSON فقط، بدون أي نص إضافي قبلها أو بعدها، بهذا الشكل بالضبط:
{
  "candidates": [
    {
      "start": <رقم بالثواني>,
      "end": <رقم بالثواني>,
      "hook_score": <رقم من 0 إلى 100>,
      "title": "<عنوان قصير بالعامية المصرية>",
      "reason": "<سبب مختصر لاختيار هذا المقطع>"
    }
  ]
}

قواعد كتابة العنوان (title) -- مهمة جداً:
- اكتب بالعامية المصرية الدارجة، مش بالفصحى، وكأنك بتحكي لصاحبك
- اكتب العنوان على هيئة سؤال يثير الفضول، لازم ينتهي بعلامة استفهام (؟)
- ممنوع الأسلوب الرسمي أو الإخباري (زي "في هذا المقطع...")
- قصير جداً (5-9 كلمات)، بيخلي حد يوقف السكرول عشان يعرف الإجابة

أمثلة على الفرق المطلوب:
- فصحى/رسمي (ممنوع): "الحديث عن أهمية الصبر في مواجهة الأزمات"
- عامية/سؤال (المطلوب): "ليه الصبر أصعب حاجة وقت الأزمة؟"

- فصحى/رسمي (ممنوع): "نصيحة قيمة حول كيفية التعامل مع الفشل"
- عامية/سؤال (المطلوب): "لو فشلت، تعمل إيه أول حاجة؟"
"""


def load_transcript_segments(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("segments", [])


def format_transcript_for_prompt(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()
        lines.append(f"[{start:.1f}s - {end:.1f}s] {text}")
    return "\n".join(lines)


def score_clip_candidates(transcript_text: str) -> dict:
    client = Groq()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"النص المفرغ مع التوقيتات:\n\n{transcript_text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


def main():
    if not os.path.isfile(TRANSCRIPT_JSON_PATH):
        print(f"Transcript file not found: {TRANSCRIPT_JSON_PATH}")
        print("Run test_whisper_arabic.py first to generate it.")
        return

    if not os.environ.get("GROQ_API_KEY"):
        print("GROQ_API_KEY is not set.")
        return

    segments = load_transcript_segments(TRANSCRIPT_JSON_PATH)
    if not segments:
        print("No segments found in transcript JSON -- nothing to score.")
        return

    transcript_text = format_transcript_for_prompt(segments)
    print(f"Loaded {len(segments)} segments. Sending to {MODEL} for hook scoring...\n")

    result = score_clip_candidates(transcript_text)
    candidates = result.get("candidates", [])

    if not candidates:
        print("Model returned no candidates. Raw result:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Sort by hook_score descending so the best clips are at the top
    candidates.sort(key=lambda c: c.get("hook_score", 0), reverse=True)

    print("=" * 70)
    print(f"TOP CLIP CANDIDATES ({len(candidates)} found)")
    print("=" * 70)
    for i, c in enumerate(candidates, 1):
        print(f"\n#{i}  Score: {c.get('hook_score')}/100")
        print(f"    Time:   {c.get('start')}s - {c.get('end')}s")
        print(f"    Title:  {c.get('title')}")
        print(f"    Reason: {c.get('reason')}")

    out_path = "hook_scoring_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nFull result saved to {out_path}")


if __name__ == "__main__":
    main()
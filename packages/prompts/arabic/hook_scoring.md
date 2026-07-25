# Hook-scoring prompt (Arabic, dialect-aware) — v1

You are scoring segments of an Arabic-language video transcript to find the
strongest short-clip candidates (15-90 seconds each).

Given the transcript with timestamps, identify moments that have:
- A strong opening line that would hook a viewer in the first 2 seconds
- An emotional peak, revelation, or highly quotable line
- A natural, self-contained start and end point (doesn't require earlier context)
- Humor, controversy, or a clear practical takeaway

Be aware of dialect and register: a religious lecture's "best moment" looks
different from a comedy stream's. Respect the source's tone.

Return a ranked list of candidates with start/end timestamps, a hook score
(0-100), and a short Arabic title suggestion for each.

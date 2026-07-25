# خُلاصة (Khulasa) — Arabic-First AI Video Clipping Platform
## Full Business & Technical Plan

*A budget-first, scalable alternative to OpusClip / Vizard / Ssemble, built for Arabic creators and the MENA market.*

---

## 1. Executive Summary

Arabic-speaking creators, podcasters, preachers, coaches, and businesses across MENA are repurposing long-form video into short clips at a fast-growing rate, but every major AI clipping tool (OpusClip, Vizard, Ssemble, Submagic, Klap) is built English-first: their transcription, "viral hook" scoring, and caption styling all silently degrade on Arabic audio, dialects, and right-to-left (RTL) text.

The plan below is for **"Khulasa"** (placeholder name — meaning "summary/essence" in Arabic; rename freely), an Arabic-first version of the same product category: upload a long video (podcast, stream, lecture, interview) → AI finds the best moments → auto-generates vertical clips with burned-in Arabic captions, auto-reframing, hook titles, and one-click scheduling.

**Core strategy:**
- **MVP on nearly-free infrastructure** — open-source models + generous free tiers (Groq, Cloudflare, Supabase) to get to market for near-$0 fixed cost.
- **Arabic-first, not Arabic-added** — dialect handling (Egyptian, Gulf, Levantine, MSA), correct RTL caption rendering, and culturally-aware content review baked into the product from day one, not bolted on.
- **Modular architecture** — every AI step (transcription, scoring, rendering) is an independently swappable service, so you can start on free/cheap providers and swap in paid, higher-throughput, or self-hosted versions as volume grows, without a rewrite.

---

## 2. Market & Competitive Landscape

### 2.1 Why now
- Short-form video consumption in MENA is high and rising, with Arabic podcast and long-form YouTube/Twitch content growing fast, but almost all repurposing tools optimize for English virality patterns and Latin-script captions.
- Arabic script is cursive, right-to-left, and context-sensitive (letters change shape depending on position), which most caption engines and generic "auto-caption" pipelines get visibly wrong — this is a real, defensible product gap, not a cosmetic one.
- Local payment rails (Fawry, Paymob, Vodafone Cash, MADA, STC Pay) are not supported by Stripe-only Western tools, creating real purchase friction for MENA solo creators.

### 2.2 Competitor snapshot

| Product | Core loop | Pricing (2026) | Arabic support | Gap you can exploit |
|---|---|---|---|---|
| **OpusClip** | Long video → AI hook-picking (GPT-based) → clips + captions + scheduler | Free (60 min/mo, watermark); Starter $15/mo; Pro $29/mo; Business custom | Captions in 20+ languages, but hook-scoring and virality model tuned on English/Western content | Dialect-aware scoring, correct RTL caption styling, MENA payments |
| **Vizard** | Similar clip pipeline, competitively priced | Creator plan around $14–15/mo | Multi-language captions, same English-centric scoring | Same as above, plus lower price point for MENA purchasing power |
| **Ssemble** | Auto clipping, face-tracking, hook titles/CTAs generated via LLM, meme/game overlays, direct scheduling, has a public API | Free tier + Pro from ~$9.90/mo | No meaningful Arabic-specific tuning found | Same gap; also a lighter competitor to benchmark UX/API design against |

**Your wedge:** none of these treat Arabic as a first-class citizen. You don't need to out-build OpusClip's whole feature surface on day one — you need to be *visibly and measurably better at the Arabic-specific parts* (transcription accuracy, caption legibility, dialect-aware "best moment" picking, and MENA-friendly pricing/payments), then expand feature-for-feature over time.

### 2.3 Positioning
"The first AI clipping tool that actually understands Arabic — dialects, script, and culture — not just translated captions."

---

## 3. MVP Product Definition

### 3.1 Core user flow (v1)
1. User pastes a YouTube link or uploads a video/audio file.
2. Platform transcribes it in Arabic (with dialect auto-detection where feasible).
3. An LLM scores segments for "hook strength" (strong opening line, emotional peak, controversial or highly quotable moment, joke, revelation) and proposes 5–10 clip candidates.
4. User picks clips (or auto-approves) → system auto-reframes to 9:16, burns in styled Arabic captions (word-by-word highlight optional), adds a hook title.
5. User downloads or schedules directly to TikTok/Instagram/YouTube Shorts.

### 3.2 Feature scope by phase

| Feature | MVP (Month 1–3) | Growth (Month 4–9) | Scale (Month 10+) |
|---|---|---|---|
| YouTube link / file ingestion | ✅ | ✅ | ✅ |
| Arabic transcription | ✅ (Whisper large-v3, MSA + major dialects) | Fine-tuned dialect model | Custom Arabic ASR, real-time |
| AI "best clip" scoring | ✅ (LLM prompt-based scoring) | Learned ranking model from user engagement data | Proprietary virality model |
| Auto-reframe / face tracking | ✅ (OpenCV/MediaPipe based) | Multi-speaker active-speaker switching | GPU-accelerated real-time preview |
| Arabic burned-in captions (RTL, correct shaping) | ✅ | Custom fonts, animated word highlight, Arabic-specific templates (Quranic/poetic style, meme style) | Full brand-kit template marketplace |
| Hook titles / CTAs | ✅ (LLM-generated in Arabic dialect of choice) | A/B tested titles | Auto-optimized based on platform performance data |
| Scheduling/publishing | Manual export only | Direct publish to TikTok/IG/YouTube via their APIs | Full social calendar, analytics loop-back |
| Team/brand workspace | ❌ | Basic (shared workspace) | Full agency tooling |
| Payments | Manual (bank transfer/Instapay) or simple Stripe | Paymob/Fawry integration | Full billing, usage-based invoicing |

### 3.3 Arabic-first requirements (the actual differentiation — don't skip these)

- **Dialect handling:** MSA (Modern Standard Arabic) transcribes cleanly with Whisper; Egyptian, Gulf, and Levantine dialects are noticeably harder. Plan for a dialect selector at upload (or auto-detect + let user correct) and budget extra QA time here — this is your core moat, so don't treat it as an afterthought.
- **RTL caption rendering:** Arabic script is contextual (letter shape depends on neighbors) and right-to-left. Naive caption burn-in pipelines (most generic FFmpeg + basic font libraries) render Arabic as disconnected, wrong-shaped letters. You need a text-shaping library (HarfBuzz) plus a bidi algorithm (fribidi) in the rendering pipeline — not just "any font that has Arabic glyphs."
- **Typography:** pick 2–3 solid Arabic web/display fonts (e.g., Cairo, Tajawal, IBM Plex Sans Arabic — all free/open-license) tuned for readability at small caption sizes on mobile.
- **Numerals & mixed content:** decide upfront whether to render Eastern Arabic numerals (١٢٣) or Western numerals (123) — this is a real user preference split across the region (Gulf vs. Levant/Egypt) and should be a per-user or per-brand setting, not hardcoded.
- **Cultural/content review:** Arabic content spans very different registers (religious lectures, comedy, political commentary, business/self-help). Your hook-scoring prompts need dialect- and context-aware tuning — a lecture's "best moment" looks nothing like a comedy stream's.
- **Right-to-left UI:** the web app itself (not just the output video) should support a full RTL layout, not just RTL text inside an LTR shell — this affects your frontend framework choice and CSS from day one.

---

## 4. Technical Architecture

### 4.1 Pipeline (see diagram above)
Ingest → Transcribe (Arabic) → LLM hook scoring → Auto-reframe & cut → Burn-in Arabic captions → Export/publish. Every stage is a separately deployable service connected by a job queue, so you can swap any one piece (e.g., move transcription from Groq's free tier to a paid, higher-SLA provider) without touching the rest.

### 4.2 MVP stack — chosen for near-zero fixed cost

| Layer | MVP choice | Why | Cost at low volume |
|---|---|---|---|
| Frontend | Next.js (App Router) + Tailwind, RTL-first layout | Free hosting on Vercel/Netlify free tier, huge ecosystem, easy RTL support | $0 |
| Auth + DB + object storage | Supabase (Postgres + Auth + Storage) | One free tier covers all three; generous limits for MVP | $0 (free tier) |
| Video/audio object storage (large files) | Cloudflare R2 | 10GB free, no egress fees (huge saving vs. S3) | $0–5/mo |
| Speech-to-text (Arabic) | Groq-hosted Whisper large-v3 (or Turbo) | Free tier: ~2,000 requests/day; paid tier ~$0.04/hour of audio if you outgrow free tier — dramatically cheaper than OpenAI's own Whisper endpoint | ~$0 to start |
| LLM (hook scoring, titles, captions polish) | Groq (Llama models, free tier) or a cheap provider (e.g., DeepSeek/Gemini Flash tier) for the heavier reasoning steps | Free/very cheap tiers with generous daily quotas | ~$0–20/mo |
| Video processing (cut, crop, encode) | FFmpeg (self-run in a worker) | Free, open source, industry standard | $0 (compute only) |
| Face tracking / auto-reframe | OpenCV + MediaPipe Face Detection | Free, open source, runs on CPU for MVP volumes | $0 |
| Arabic text shaping for captions | HarfBuzz + fribidi (called from the FFmpeg/Python render step) | Free, open source — this is the piece most competitors get wrong for Arabic | $0 |
| Background jobs / GPU render bursts | Modal.com or RunPod serverless (pay-per-second GPU) | No idle cost — you only pay while a video is actually rendering; both offer free starter credits | Near-$0 at MVP scale, scales linearly |
| Payments | Stripe (international) + Paymob or Fawry (Egypt/MENA local rails) | Stripe free until you take payments; Paymob/Fawry take a per-transaction cut, no fixed fee | Transaction-based only |
| Monitoring/error tracking | Sentry free tier | Enough for MVP | $0 |
| Email/notifications | Resend or Supabase's built-in email | Free tier sufficient at low volume | $0 |

**Estimated MVP fixed monthly cost: $0–30/month** for the first few hundred users, assuming you stay inside free tiers and pay only for occasional GPU render bursts and Whisper minutes beyond the free quota.

### 4.3 Detailed pipeline, tool by tool

1. **Ingestion:** `yt-dlp` (free, open source) to pull YouTube audio/video by URL; direct upload goes straight to Cloudflare R2.
2. **Transcription:** send audio to Groq's Whisper endpoint with Arabic language hint; store word-level timestamps (needed later for word-by-word caption highlighting).
3. **Hook scoring:** feed the transcript (with timestamps) to an LLM with a carefully engineered Arabic-language prompt asking it to identify: strong openings, emotional peaks, quotable lines, natural clip boundaries (15–90 seconds), and to score each candidate's "hook strength." This is pure prompt engineering at MVP stage — no custom model training needed yet.
4. **Cutting & reframing:** FFmpeg extracts the chosen segment; MediaPipe detects the active speaker's face per frame and computes a smooth vertical (9:16) crop window; FFmpeg renders the cropped, reframed video.
5. **Caption burn-in:** generate an `.ass` (Advanced SubStation Alpha) subtitle file with correct Arabic shaping via HarfBuzz/fribidi, styled per template (font, color, word-highlight animation), then burn in with FFmpeg's `libass` filter.
6. **Export/delivery:** final MP4 stored in R2, signed download URL served to the user; Phase 2 adds direct publish via TikTok/Instagram/YouTube's official content APIs.

### 4.4 Data model (minimal MVP schema)
- `users` (auth, plan tier, locale/dialect preference)
- `projects` (source video metadata, status)
- `transcripts` (word-level timestamps + speaker labels)
- `clip_candidates` (start/end, hook score, generated title)
- `renders` (final video asset references, render status/job id)
- `usage_ledger` (minutes transcribed, clips rendered — for metering/billing)

### 4.5 Scaling path — how the same architecture grows with you

| Trigger | What changes | Why it's easy |
|---|---|---|
| Free-tier ASR quota exceeded | Switch to paid Groq tier or add Deepgram/ElevenLabs as a second provider behind the same internal "transcribe()" interface | Because transcription is an isolated service call, swapping providers is a config change, not a rewrite |
| CPU-based face tracking too slow at volume | Move rendering workers to GPU-backed serverless (Modal/RunPod) full time instead of ad hoc | Same worker code, just a different execution target |
| LLM prompt-based scoring plateaus in quality | Fine-tune a smaller open model (e.g., a Llama variant) on your own labeled "good clip / bad clip" data collected from user picks | You'll have accumulated exactly the training data you need from MVP usage logs |
| Free-tier database/storage limits hit | Upgrade Supabase plan or migrate Postgres to a managed provider (still Postgres — no schema rewrite) | Standard Postgres underneath the whole time |
| Need real-time/streaming clipping (live streams) | Add a streaming ASR path (Groq/Deepgram streaming) and a hot-clip detection service in parallel with the batch pipeline | Batch and streaming can coexist; you're adding a path, not replacing one |
| Direct social publishing needed | Integrate TikTok Content Posting API, Instagram Graph API, YouTube Data API | Additive service, doesn't touch core pipeline |

---

## 5. Cost Model & Unit Economics

### 5.1 Approximate cost per minute of source video processed (MVP stack)
- Transcription: ~$0.0006–0.04/hour of audio depending on Groq tier used → effectively fractions of a cent per minute
- LLM scoring/titles: a few thousand tokens per video → typically under $0.01–0.05 per video on cheap providers
- Rendering compute (GPU burst): a few cents per clip depending on length and resolution
- **Realistic all-in cost per finished clip at MVP scale: well under $0.10**, meaning even a $5–10/month plan is comfortably profitable once you're past free-tier ceilings.

### 5.2 When costs actually start to matter
At low volume (say, under 500 processed videos/month), you can likely run this **entirely inside free tiers** except for occasional overage. The point where you need to budget seriously is when you cross into thousands of videos/month — at which point your paying user base should already be covering the (still very low, cents-per-clip) marginal cost.

---

## 6. Business Model & Pricing

Freemium, metered by "processing minutes" (same mental model as OpusClip, which the market already understands), priced for MENA purchasing power in both USD and local currency:

| Tier | Price | Included | Target user |
|---|---|---|---|
| Free | $0 | ~60 min/month, watermark, 3–7 day storage | Trial users, students |
| Creator | ~$7–9/mo (or local equivalent via Paymob/Fawry) | ~150–200 min/month, no watermark, dialect selection, basic templates | Solo creators, podcasters |
| Pro | ~$15–19/mo | More minutes, direct publish/scheduling, brand templates, priority render queue | Growing creators, small brands |
| Business/Agency | Custom | Team seats, API access, white-label export, dedicated support | Agencies, media companies, mosques/da'wah organizations managing multiple channels |

Pricing meaningfully below OpusClip/Vizard's USD pricing (which is expensive relative to regional income) is itself a competitive weapon in this market, not just a nice-to-have.

---

## 7. Go-to-Market for MENA

- **Seed with Arabic podcast networks and YouTube interview shows** — these are your best source of long-form content and the most obvious repurposing use case; offer free processing in exchange for case studies/testimonials.
- **Partner with Arabic content creator communities** (Discord/Telegram groups, university media clubs, gaming/streaming communities) for early access and feedback.
- **Da'wah/religious lecture channels** are an underserved, high-volume, low-churn niche — long-form lectures are a natural fit for clipping, and this audience is currently ignored by Western tools.
- **Local-language content marketing:** publish your own before/after clip comparisons (generic tool vs. yours) showing caption quality differences — this is a highly visual, shareable proof point.
- **Referral/affiliate program** for creators, since this audience already has engaged followings who trust their recommendations.

---

## 8. 12-Month Roadmap

| Phase | Timeframe | Milestone |
|---|---|---|
| 0 — Validate | Weeks 1–4 | Manual/semi-automated pipeline (even a script + Whisper + FFmpeg you run yourself for 10–20 pilot users) to prove people want Arabic-tuned clips before building the full app |
| 1 — MVP | Months 1–3 | Self-serve web app on the free-tier stack above; core loop working end to end for MSA + 1–2 dialects |
| 2 — Growth | Months 4–9 | Direct social publishing, team workspaces, MENA payment rails, dialect coverage expansion, first paid tiers live |
| 3 — Scale | Months 10–12 | Fine-tuned scoring model from usage data, GPU infra fully provisioned, agency/API tier, possible fundraising conversation if metrics justify it |

---

## 9. Team, Legal & Operations

- **Minimum viable team:** 1 full-stack/AI engineer (you, likely) + part-time Arabic content/QA reviewer to sanity-check transcription and hook-scoring quality across dialects — this role matters more than it looks and is cheap to staff regionally.
- **Legal basics:** clear ToS on copyright (you are processing user-uploaded/linked content, not hosting pirated media — make users attest they have rights to the source); data retention policy (how long source videos/clips are stored); privacy policy covering any biometric-adjacent processing (face detection for reframing — disclose this clearly, don't store facial data beyond the render job).
- **Not legal/financial advice:** payment processor and business registration requirements (e.g., whether you need a local entity to use Paymob/Fawry, VAT treatment of a SaaS subscription in your country) vary and are worth a short consult with a local accountant/lawyer before you take real payments.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Free-tier AI providers change pricing/limits (this happens often) | Keep every AI call behind an internal interface so swapping providers is a config change, not a rewrite; never hardcode a single vendor's SDK deep into business logic |
| Arabic dialect transcription quality disappoints early users | Set expectations clearly per dialect at launch (e.g., "excellent for MSA and Egyptian, good for Gulf, improving for Levantine"); collect correction data from users to improve over time |
| Copyright/rights issues from clipped content | Require user attestation of rights at upload; respond promptly to takedown requests; avoid processing content you have reason to believe is unauthorized |
| Underestimating GPU/render costs at scale | Track cost-per-clip from day one in the usage ledger table so pricing tiers stay profitable as you grow |
| Competitors add Arabic support | Your moat is depth (correct RTL shaping, dialect nuance, cultural context in scoring, MENA payments/pricing) — keep investing there rather than chasing feature parity on everything else |

---

## 11. Key Success Metrics (KPIs)

- Time-to-first-clip for a new user (activation)
- % of AI-suggested clips a user actually exports without heavy manual editing (scoring quality proxy)
- Caption correction rate per dialect (transcription quality proxy)
- Free-to-paid conversion rate
- Cost per processed minute vs. revenue per processed minute (unit economics health)
- Monthly retained processing minutes per paying user (engagement/stickiness)

---

*This plan is a starting framework — validate the manual/semi-automated version (Phase 0) with real Arabic creators before writing a line of app code. The biggest risk here isn't the tech stack, it's whether dialect-aware clipping is a strong enough wedge to win users away from tools they already know. Test that first, cheaply.*

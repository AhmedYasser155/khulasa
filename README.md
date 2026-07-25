# Khulasa — Arabic-first AI video clipping platform

Monorepo scaffold. See PLAN.md (business/technical plan) for context.

## Structure
- `apps/web` — Next.js frontend (RTL-first). Scaffold with `pnpm create next-app`.
- `apps/worker` — Python FastAPI worker: ingest, transcribe, score, render, captions.
- `packages/prompts` — versioned Arabic prompt templates for hook-scoring and captions.
- `infra` — docker-compose + Dockerfile for local dev.

## Quick start (Windows)
1. Install: Node.js 20+, pnpm (`npm install -g pnpm`), Python 3.11+, Docker Desktop.
2. Copy `.env.example` to `.env` and fill in keys (Supabase, Groq, R2).
3. Scaffold the frontend (one-time, interactive):
   `cd apps\web` then `pnpm create next-app@latest . --typescript --tailwind --app --src-dir --import-alias "@/*" --eslint`
4. Start the worker:
   `cd infra` then `docker compose up --build`
5. Start the frontend:
   `cd apps\web` then `pnpm install` then `pnpm dev`

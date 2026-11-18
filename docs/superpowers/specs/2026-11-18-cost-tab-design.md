# Cost tab: design

## Intent
See what Jarvis's model use costs, priced at Google's paid-tier rates. The AI Studio key is on the free tier and
Google sign-ins (Antigravity) bill nothing, but the user wants every token counted as if billed ("count all the tokens
used as the ones used in paid tier").

## Goals
- Tokens and estimated USD per model and per day, for today, the last 7 days and the last 30 days.
- Everything that calls a model counts: the agent, look/point/search/image, hearing and speaking, WhatsApp replies,
  learning, and the voice (Gemini Live, audio priced as audio), WhatsApp calls included.
- Nothing leaves the PC: no account, works offline.

## Non-goals
- Matching a real bill; Langfuse; budgets or alerts (can come later).
- Google Search grounding fees ($14 per 1,000 after 5,000 free a month): not counted, said on the page.

## Approaches
1. **Native in Jarvis (picked by the user).** Each backend keeps the reply's token counts; a built-in price list prices them.
2. Langfuse Cloud: Jarvis sends model and token counts to Langfuse, which prices them; the tab reads its Metrics API.
   Needs an account and keys, and data leaves the PC.
3. Native plus an optional Langfuse export: more moving parts for no need stated yet.

Self-hosted Langfuse was ruled out: Docker with Postgres, ClickHouse, Redis and S3 for a desktop assistant.

## How
- **Recording.** Gemini replies carry `usageMetadata` (prompt, candidates, thoughts, cached, tool-use prompt, per-modality
  details); OpenAI-compatible ones carry `usage`; Gemini Live sends `usage_metadata` per request. Each is turned into
  `{in: {modality: tokens}, out: {modality: tokens}, cached: tokens}` (thinking counts as output, cached tokens are
  taken out of the input) and added to `DATA/usage.json` under the day and `"backend model"`, beside the request count
  the Health page already shows. 90 days are kept.
- **Prices.** A built-in table (USD per 1M tokens, Google's pricing page on 2026-11-18), with dated changes: 3.8 Flash
  and the TTS models double on 2027-01-01, so each day is priced at its own prices. Antigravity uses the same table as
  AI Studio (same models). A price per modality where Google has one (Live audio $3 in / $12 out), else the text price.
  Models with no known price (gemini-3.7-flash isn't on the page any more, other providers) show their tokens and "no
  price". No price editor: the user said the built-in prices are enough.
- **Page.** "Cost" in the rail, after Memory. Period chips (Today, 7 days, 30 days); the total at paid-tier prices with
  the tokens behind it; a bar per day; a row per model (requests, tokens in and out, cost), costliest first; a line
  saying nothing is billed on the free tier and that search fees aren't counted.
- **API.** `GET /api/cost?days=N` → `{total, days: [{day, cost}], models: [{key, requests, input, output, cost|null}]}`;
- Every text translated (18 languages); `docs/screens.py` gets made-up data; one screenshot of the finished page.

## Decided along the way (the user, 2026-11-18)
- Gemini 4 Hydrogen ($1.50 in / $7.50 out) is in the price table and first in the background tasks' list ("whatever you
  want" after being shown it took 35-40 s per reply on the free key and refuses "minimal" thinking, Search, pictures
  and speech). Several API keys per provider already exist (Models page, "Paste another key").

## Left to the builder
Exact layout within the glass look and its tokens; how unknown modalities fall back; rounding (cents, or tenths of a
cent below $0.01).

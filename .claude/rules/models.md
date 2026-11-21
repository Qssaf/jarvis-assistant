---
paths:
  - "**/brain.py"
  - "**/local_backends.py"
  - "**/qml/ModelsPage.qml"
  - "**/qml/CostPage.qml"
  - "**/qml/HealthPage.qml"
---

# Models, backends and Google sign-in

Part of this repository's architecture notes (the rest: `CLAUDE.md` and the other files here). Each paragraph is how
that part works and what broke before.

**Models per job.** `MODEL_JOBS` (agent, look, point, point_strong, search, image, and the backup voice's hear and speak) each run on `models_for(job)`: the
`<job>_models` setting (lines `"backend model thinking"`) or the built-in list. `_generate` skips entries in
`down_until`; a 429 with `PerDay` pauses that model until the Pacific-midnight reset (`quota_reset_in`), and when every
entry is marked down (a network blip) the first "not answering" one is tried anyway. `count_use` keeps today's requests
per model for the Health page. Every backend also records its reply's tokens (`count_tokens` with `gemini_usage` /
`openai_usage`; Gemini Live's per-request `usage_metadata` through `count_live`, WhatsApp calls too) in `usage.json`
(90 days); `cost_report` prices them from `PRICES` (Google's paid tier, dated tiers, per modality) for the Cost page.
Gemini 4 Hydrogen's speed depends on the route (measured 2026-11-20): `antigravity gemini-4-hydrogen-sonar` answers a task
step or a look in about 3 s, `aistudio gemini-4-hydrogen` in 17-25 s whatever the prompt or thinking, so that route has
60 s in `SLOW_ROUTES` (at "low"'s 20 s half its replies were cut off, and the "hi" probes ate its quota). Both are in
`agent_models` only, after aistudio gemini-3.8-flash medium: it refuses "minimal" thinking with a
400, and on the free key it answered in 35-40 s, hit 503s and used its daily quota up in about ten requests (first in
the list it answered 0 of 191 task steps, and each step waited 8 s for it).

**Backends.** `AIStudio` (Gemini's native API) plus `OpenAICompatible` for every provider in `brain.providers()`
(built-ins, the user's `providers.json`, Ollama). `Brain.backend(name)` builds them lazily, and `forget_backend` runs
after a key changes. `to_openai`/`from_openai` translate between the Gemini-format history the agent keeps and the
OpenAI chat format; Gemini thought signatures ride along as `thoughtSignature` parts and are only sent to Google hosts.
Keys live in the OS keychain via `store.secret`/`set_secret`, falling back to a 0600 `keys.json`; tests force the file
fallback with `PYTHON_KEYRING_BACKEND`. A provider may have several (`store.secrets`: one keychain entry, a key per
line; `secret` is the first): `brain.Keys` uses one at a time inside the backend, below the model chain (the one that
answered last stays; `http_error`'s `key=True`, a 429, 401/403 or Gemini's 400 `API_KEY_INVALID`, rests it, per model
for a limit, for all for `KEY_REST` when refused), and the chain only sees `Overloaded` once every key rests. One key
behaves as before. Gemini Live tries each of `gemini_keys()` once per session open (`Live._next_key`,
`brain.live_key`, which WhatsApp's calls follow). The window only ever gets a key's last four characters. The voice uses Gemini Live; when Live can't be opened (`Live._fall_back`, retried
after `LIVE_RETRY`) or `always_backup_voice` is on, `Backup` (jarvis.py) takes Live's mic, typed text and announcements:
it cuts requests at a pause, `Brain.hear` writes them down, `Brain.ask` answers, `Brain.speak` (or `system.speech_wav`)
says it. `hear`/`speak` are `MODEL_JOBS` whose failures all move on to the next model (`_speech`, no probes).

**Google sign-in.** The `antigravity` backend (brain.py) uses Google accounts signed in from the Models page
(`google_sign_in`: Antigravity's OAuth client, read by `google_client()` from the opencode Antigravity plugin
(`PLUGIN_REPO`, found through `opencode.json` first) or the env file and never committed (GitHub's push protection blocks it), PKCE, a callback on `localhost:51121`, then `loadCodeAssist` /
`onboardUser` for the account's project) plus any from the opencode plugin's `antigravity-accounts.json`. A request asks
each account once at most: a 429 rests that account for that model (`Antigravity.resting`, as long as `limit_info` reads
from the reply; the plugin's `rateLimitResetTimes` count too) and the next one is asked, except
`MODEL_CAPACITY_EXHAUSTED` (no account's fault: not sprayed over the others); a 403 "disabled in this account" rests the
account for good, another 401/403 for 10 min; with every account resting it raises `Overloaded` with `retry_after` (so
no "hi" probe) and sends nothing. Waits follow the Antigravity CLI (`agy_delay`, by `refusals` in a row per account
and model, reset by an answer; never shorter than Google's delay): a 429's rest and a 5xx's `retry_after`. A timeout or
lost connection carries `retry_after` 30 s, a 404 an hour: the CLI never sends "hi" probes, and it has no pacing of
its own, so neither has Jarvis. One account at a time: `idx` (the one that answered last) takes every model's
requests until it can't, and on opencode's accounts it's set to the plugin's `activeIndexByFamily` one whenever that
changes (`followed`), so the two apps aren't on two accounts at once. A refused token refresh is `Overloaded` too, never `BadRequest` (that would stop the
whole model chain).
Warned about (Google may suspend accounts used this way); not opt-in for opencode's accounts: `google_accounts` uses that
file whenever it exists (enabled ones only; `projectId`-only accounts, added from the plugin's menu, are valid). With no account its constructor raises
`LookupError`, so its entries (first in every built-in list) are skipped and Brain says nothing. Tests point
`OPENCODE_ACCOUNTS` and `PLUGIN_CONSTANTS` at temp files.

**Backends in code.** A gitignored `local_backends.py`, imported at the end of
brain.py, may register more classes in `brain.BACKENDS` and prepend entries to the model lists (`LOOK_MODELS`,
`POINT_MODELS`, `SEARCH_MODELS`, `IMAGE_MODELS`).

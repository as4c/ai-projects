# Quickstart — Swipe-to-Talk Voice Avatars

Zero → a working voice call with an AI avatar. ~10 minutes.

**What you're starting:** three processes.

1. **Django** — the product API (avatars, match, sessions) on `:8000`
2. **Voice bot** — the Pipecat WebRTC voice agent on `:7860`
3. **Test client** — a browser page on `:5500` to drive a call

```
browser (test client :5500)
   │  GET /avatars, POST /match, POST /end   ──────────►  Django :8000
   │  WebRTC voice call (SDP + audio)         ──────────►  Bot :7860 ── STT→LLM→TTS
```

---

## 0. Prerequisites

- The repo's Python venv with deps installed. **Pipecat lives in the venv you `pip install`ed into** (this repo has both `venv` and `.venv` — use that one; examples below use `.venv`).
- Three API keys (all have free tiers):
  - **OpenRouter** — openrouter.ai → LLM (the words)
  - **Deepgram** — console.deepgram.com → speech-to-text ($200 free credit)
  - **Cartesia** — play.cartesia.ai → text-to-speech (the voices)
- A **JWT access token** for a logged-in user (to call the authed APIs).

---

## 1. Add your keys

Edit `envs/dostt/local_dev_config.env` and fill:

```bash
OPENROUTER_API_KEY="sk-or-..."
DEEPGRAM_API_KEY="..."
CARTESIA_API_KEY="..."

# let the browser test client talk to Django
DJANGO_CORS_ALLOWED_ORIGINS="http://localhost:5500"
```

(The `VOICE_*` keys already have working local defaults.)

---

## 2. Install deps

```bash
# Django deps: already in the repo venv.
# Voice bot deps (into the SAME venv, so it can read Django settings):
pip install -r requirements/base.txt
```

---

## 3. Migrate + run Django  (terminal 1)

```bash
export APP_NAME=dostt DEPLOYMENT=local_dev
python manage.py migrate       # creates the voice_avatars table
python manage.py runserver     # :8000
```

---

## 4. Run the voice bot  (terminal 2)

```bash
python voice_agent/agent.py
# -> "voice agent listening on :7860 (POST /voice-agent/connect)"
```

> The bot reads all config from Django settings at startup. **Any env change (keys, model,
> URLs) needs a bot restart** to take effect.

---

## 5. Run the test client  (terminal 3)

Must be served over `http://localhost` (mic needs a secure context; `file://` won't work):

```bash
cd testclient
python3 -m http.server 5500      # open http://localhost:5500
```

---

## 6. Make a call

1. Open `http://localhost:5500`.
2. Paste **Django base URL** (`http://localhost:8000`) and your **JWT access token**
   (raw token — the page adds the header).
3. **Load avatars** → 8 personas. Aria / Meera / Priya speak **Hindi**; the rest English.
4. **Talk** on a card → allow mic → speak. The avatar replies in its own voice.
   Talk over it to test barge-in.
5. Hang up → the call ends and duration is recorded.

That's the full loop: **swipe → match → live voice call → end.**

---

## Troubleshooting (the exact things that trip people)

| Symptom                                                            | Cause → Fix                                                                                                                                                                                        |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `401 {"detail":"Authentication credentials were not provided."}` | Wrong auth header. This app uses**`JWT-Authorization: Bearer <token>`**, NOT `Authorization`. Paste only the raw `eyJ…` token.                                                         |
| Browser shows**CORS error** (works in Postman)               | Django doesn't allow the page origin / custom header. Set`DJANGO_CORS_ALLOWED_ORIGINS="http://localhost:5500"` **and restart Django**. The `jwt-authorization` header is already allowed. |
| `avatars error: Failed to fetch`                                 | Django not running, wrong base URL (http vs https), or`localhost` vs `127.0.0.1` origin mismatch. Keep both the page and base URL on the same host.                                             |
| Bot:`voice ID must be a valid UUID`                              | A persona's`voice_id` is a placeholder. Use a real Cartesia voice UUID.                                                                                                                           |
| Bot:`not a valid model ID` / `No endpoints found`              | Bad/typo'd or deprecated OpenRouter model. Verify the slug at openrouter.ai/models.                                                                                                                 |
| Env change had no effect                                           | The process reads env**at startup** → **restart** it (Django for API/CORS keys, the bot for its keys/model).                                                                           |
| No audio on a**phone / different network**                   | WebRTC media is UDP peer-to-peer. Across NAT you need a**public `bot_url`** + a **TURN server** (`VOICE_TURN_*`). Same machine works without it.                                |
| Replies take 5–10s                                                | Slow/reasoning LLM. Use a fast model (`google/gemini-2.5-flash`, `openai/gpt-4o-mini`).                                                                                                         |

---

## Where things live

|                                  |                                         |
| -------------------------------- | --------------------------------------- |
| Personas (8 avatars)             | `personas.py`                         |
| API (avatars/match/end/internal) | `views.py`, `urls.py`               |
| Voice bot                        | `voice_agent.py`                          |
| Browser test client              | `testclient/index.html`               |
| Regenerate voice intros          | `scratchpad/gen_intros.py` (Cartesia) |
| Frontend integration guide       | `FRONTEND_INTEGRATION.md`             |
| API contract (curl)              | `API.md`                              |
| Full details                     | `README.md`                           |

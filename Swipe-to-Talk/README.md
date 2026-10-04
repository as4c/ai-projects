# Voice Avatars (swipe-to-talk)

Two deployable services:

1. **Avatars API** — Django + DRF (`voice_avatars/`) — personas, sessions, spend gate
2. **Voice agent** — Pipecat WebRTC (`voice_agent/`) — Deepgram STT → OpenRouter LLM → Cartesia TTS

```
Frontend / testclient
   │  Token auth:  /voice-avatars/avatars|match|end
   ▼
Avatars API :8000  ──HTTP internal──►  Voice agent :7860  ◄── WebRTC
                                            │
                               mic → VAD → STT → LLM → TTS → speaker
```

## Layout

```
voice-avatars/
  Dockerfile                 # Avatars API image
  requirements.txt           # API deps only
  manage.py / config / voice_avatars/
  voice_agent/
    agent.py
    requirements.txt         # Pipecat / STT / TTS deps
    Dockerfile               # Voice agent image
  testclient/
  docs/
```

## Local run

```bash
cd /Users/mac/Documents/lokal/voice-avatars
python3 -m venv .venv && source .venv/bin/activate

# API deps
pip install -r requirements.txt
# Agent deps (same venv is fine for local)
pip install -r voice_agent/requirements.txt

cp .env.example .env
# fill OPENROUTER_API_KEY, DEEPGRAM_API_KEY, CARTESIA_API_KEY

python manage.py migrate
python manage.py runserver          # :8000
python voice_agent/agent.py         # :7860
```

Open `testclient/index.html` → **Get demo token** → match / call.

## Docker (two images)

```bash
# Avatars API
docker build -t voice-avatars-api .
docker run --rm -p 8000:8000 --env-file .env voice-avatars-api

# Voice agent (build context = voice_agent/)
docker build -t voice-agent ./voice_agent
docker run --rm -p 7860:7860 --env-file .env \
  -e VOICE_DJANGO_URL=http://host.docker.internal:8000 \
  voice-agent
```

`VOICE_BOT_AUTH_KEY` must match on both sides. Agent reaches the API via `VOICE_DJANGO_URL`.

## API surface

| Method + path | Auth | Purpose |
|---|---|---|
| `POST /api/demo-login/` | none | Demo token |
| `GET /voice-avatars/avatars/` | `Authorization: Token …` | Public personas |
| `POST /voice-avatars/match/` | Token | Create session → `{session_id, bot_url}` |
| `POST /voice-avatars/{id}/end/` | Token | Record duration |
| `GET /voice-avatars/{id}/internal/` | `x-voice-bot-key` | Private prompt/voice for agent |
| `POST :7860/voice-agent/connect` | none | WebRTC SDP |
| `GET :7860/health` | none | Agent liveness |

## Notes

* Agent does **not** import Django — config is env / `.env` only.
* In-memory WebRTC peers → keep agent at **1 replica** (or sticky sessions).
* Mobile / cross-NAT audio needs TURN (`VOICE_TURN_*`).

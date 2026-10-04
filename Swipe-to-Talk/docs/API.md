# Hackathon · Swipe-to-Talk — Frontend API Contract

Base URL: `https://innocent-swine-roughly.ngrok-free.app`

These are the only endpoints the **frontend** integrates. (An internal
bot-only endpoint exists server-side but is never called by the client.)

## Auth

Every request below needs the user's access token in a **custom** header —
`JWT-Authorization: Bearer <token>` (this app uses `JWT-Authorization`, **not**
the standard `Authorization`).

```bash
TOKEN='eyJhbGciOi...your access token...'      # raw JWT, no "Bearer"
```

> Through ngrok, add `-H "ngrok-skip-browser-warning: 1"` if you ever get an HTML
> interstitial instead of JSON.

---

## 1. List avatars

`GET /voice-avatars/avatars/` — the swipe deck.

```bash
curl -sS "https://innocent-swine-roughly.ngrok-free.app/voice-avatars/avatars/" \
  -H "JWT-Authorization: Bearer $TOKEN" | jq
```

**200 OK**:

```json
{
  "avatars": [
    {
      "id": 1,
      "name": "Aria",
      "age": 24,
      "location": "Delhi",
      "avatar_image_url": "https://api.dicebear.com/9.x/avataaars/png?seed=aria&size=400",
      "voice_intro_url": "http://localhost:5500/intros/aria.mp3",
      "interests": ["Astrology", "Tarot", "Meditation"],
      "conversation_topics": ["Career decisions", "Relationship advice", "Daily motivation"],
      "personality_traits": ["Warm", "Intuitive", "Patient"]
    }
    // ... ids 2-8: Kiara, Meera, Diya, Ishita, Riya, Priya, Naina
  ]
}
```

**401 Unauthorized** — missing/invalid token:

```json
{ "detail": "Authentication credentials were not provided." }
```

Render the deck from this. Tap-to-play `voice_intro_url`. Left-swipe = next card
(no API call). Right-swipe = call **Match** (§2).

---

## 2. Match (right-swipe)

`POST /voice-avatars/match/` — creates a session and returns the voice-call connection info.

```bash
curl -sS -X POST "https://innocent-swine-roughly.ngrok-free.app/voice-avatars/match/" \
  -H "JWT-Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"avatar_id": 1}' | jq
```

**201 Created**:

```json
{
  "session_id": "20d8718c-33dc-40cf-9576-6cb060c6b1fe",
  "avatar": { "id": 1, "name": "Aria", "...": "same public fields as §1" },
  "bot_url": "http://localhost:7860/voice-agent/connect"
}
```

**400 Bad Request** — unknown avatar id: `{ "error": "unknown_avatar" }`

**402 Payment Required** — locked (past free interactions), show the unlock screen:

```json
{ "error": "locked", "reason": "min_spend" }
```

On `201`, connect the voice call to `bot_url` with `session_id` (§3).

---

## 3. Start the voice call (WebRTC)

Open a WebRTC audio connection to the `bot_url` from §2, passing `session_id`.
This is **not** a REST call — use the Pipecat web client SDK
(`@pipecat-ai/client-js` + `@pipecat-ai/small-webrtc-transport`) or a raw
`RTCPeerConnection`. The SDK captures the mic and plays the reply.

Raw signaling shape (what the SDK does under the hood): `POST {bot_url}` with a JSON
body `{ sdp, type: "offer", session_id }` → returns `{ sdp, type: "answer", pc_id }`,
then audio streams over the peer connection.

Drive UI from the client events: `botStartedSpeaking`, `userStartedSpeaking`
(barge-in), `disconnected`.

When the user hangs up → call **End** (§4).

---

## 4. End call (hang-up)

`POST /voice-avatars/{session_id}/end/` — records call duration.

```bash
SESSION=20d8718c-33dc-40cf-9576-6cb060c6b1fe
curl -sS -X POST "https://innocent-swine-roughly.ngrok-free.app/voice-avatars/$SESSION/end/" \
  -H "JWT-Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"duration_seconds": 72}' | jq
```

**200 OK**:

```json
{ "duration_seconds": 72, "next_locked": false }
```

**404 Not Found** — unknown session: `{ "error": "not_found" }`

---

## Quick reference

| # | Method | Path                             | Body                      | Success                                                 |
| - | ------ | -------------------------------- | ------------------------- | ------------------------------------------------------- |
| 1 | GET    | `/voice-avatars/avatars/`          | —                        | `200 {avatars:[...]}`                                 |
| 2 | POST   | `/voice-avatars/match/`            | `{avatar_id}`           | `201 {session_id, avatar, bot_url}` · `402 locked` |
| 3 | —     | WebRTC to`bot_url`             | SDP offer +`session_id` | audio call                                              |
| 4 | POST   | `/voice-avatars/{session_id}/end/` | `{duration_seconds}`    | `200 {duration_seconds, next_locked}`                 |

**Flow:** `avatars` → right-swipe → `match` → WebRTC call to `bot_url` → hang up → `end`.
All REST calls use the `JWT-Authorization: Bearer <token>` header.

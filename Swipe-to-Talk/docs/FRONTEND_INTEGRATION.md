# Swipe-to-Talk — Frontend Integration Guide

Everything the frontend needs to wire up: what to **send**, what comes **back**, and
how to start the voice call. The UI is built; this is the API layer.

- **Base URL:** `https://innocent-swine-roughly.ngrok-free.app`
- **Voice bot:** `bot_url` is returned by the Match API (do not hardcode it).
- A **working reference implementation** of the whole flow (including the WebRTC call)
  lives at `testclient/index.html` — copy its logic.

---

## 0. Auth (read this first)

Every REST call needs the logged-in user's access token in a **custom header**:

```
JWT-Authorization: Bearer <access_token>
```

⚠️ It is **`JWT-Authorization`**, NOT the standard `Authorization`. Using the wrong
header returns `401 {"detail":"Authentication credentials were not provided."}`.

Also send `Content-Type: application/json` on POSTs. Through ngrok, if you ever get an
HTML page instead of JSON, add header `ngrok-skip-browser-warning: 1`.

---

## Local dev (running the RN app on your own machine)

If the backend + bot run on **your machine** and you run the RN app locally, you need
**no ngrok and no TURN** — client and bot are on the same machine/LAN, so WebRTC connects
directly. Just point the app at the right host and allow HTTP + mic.

**1. Host address depends on how you run RN** (`localhost` differs per target):

| RN target | Django base URL | `bot_url` host |
|---|---|---|
| iOS Simulator | `http://localhost:8000` | `http://localhost:7860` |
| Android Emulator | `http://10.0.2.2:8000` | `http://10.0.2.2:7860` |
| Physical phone (same Wi-Fi) | `http://<mac-LAN-IP>:8000` | `http://<mac-LAN-IP>:7860` |

Find the LAN IP with `ipconfig getifaddr en0` (e.g. `192.168.31.135`). Set the Django
base URL in the app config; ask backend to set `VOICE_BOT_URL=http://<host>:7860/voice-agent/connect`
(same host form) and **restart Django** so `match` returns it.

**2. Allow plain HTTP in dev** (you're hitting `http://`, not `https://`):

- iOS `Info.plist`:
  ```xml
  <key>NSAppTransportSecurity</key>
  <dict><key>NSAllowsLocalNetworking</key><true/></dict>
  ```
- Android `AndroidManifest.xml`: `<application android:usesCleartextTraffic="true" ...>`

**3. Mic permission:**

- iOS `Info.plist`: `NSMicrophoneUsageDescription`
- Android `AndroidManifest.xml`: `<uses-permission android:name="android.permission.RECORD_AUDIO"/>` + request at runtime before connecting.

**Notes**
- **No TURN / no ngrok / no CORS** needed for same-machine/LAN dev (CORS is browser-only;
  native RN ignores it). Leave `VOICE_TURN_*` blank.
- Most reliable WebRTC targets: **iOS Simulator** or a **physical phone on the same Wi-Fi**.
  The Android Emulator's virtual router can complicate media — if audio misbehaves, test on
  a real device via the Mac's LAN IP.
- TURN + a public `bot_url` are only needed once the app and bot are on **different
  networks** (staging / real devices over cellular).

---

## Types (TypeScript)

Field names are **snake_case** (map to your camelCase as you like).

```ts
interface Avatar {
  id: number;                       // 1..8
  name: string;
  age: number;
  location: string;
  avatar_image_url: string;
  voice_intro_url: string;          // playable mp3
  interests: string[];
  conversation_topics: string[];
  personality_traits: string[];
}

interface AvatarsResponse { avatars: Avatar[]; }

interface MatchResponse {
  session_id: string;               // uuid — use for the call + end
  avatar: Avatar;
  bot_url: string;                  // WebRTC endpoint for the voice call
}

interface MatchLocked { error: "locked"; reason: "min_spend"; }   // HTTP 402

interface EndResponse {
  duration_seconds: number;
  next_locked: boolean;             // true => next match will be 402
}
```

---

## 1. Get avatars (the deck)

**Send**

| | |
|---|---|
| Method | `GET` |
| Path | `/voice-avatars/avatars/` |
| Headers | `JWT-Authorization: Bearer <token>` |
| Body | — |

**Get back — `200 OK`**

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
    // ... ids 2..8 (Kiara, Meera, Diya, Ishita, Riya, Priya, Naina)
  ]
}
```

**Errors:** `401` (bad/missing token).

**UI:** render the deck. Tap-to-play `voice_intro_url`. **Left swipe** = show next card
(no API call). **Right swipe** = call Match (§2).

```bash
curl -sS "https://innocent-swine-roughly.ngrok-free.app/voice-avatars/avatars/" \
  -H "JWT-Authorization: Bearer $TOKEN"
```

---

## 2. Match (on right-swipe)

Creates a call session and returns where to connect the voice call.

**Send**

| | |
|---|---|
| Method | `POST` |
| Path | `/voice-avatars/match/` |
| Headers | `JWT-Authorization: Bearer <token>`, `Content-Type: application/json` |
| Body | `{ "avatar_id": 1 }`  ← the `id` from the avatar (number or string both work) |

**Get back — `201 Created`**

```json
{
  "session_id": "20d8718c-33dc-40cf-9576-6cb060c6b1fe",
  "avatar": { "id": 1, "name": "Aria", "…": "same fields as §1" },
  "bot_url": "http://localhost:7860/voice-agent/connect"
}
```

**Errors**

- `400 {"error":"unknown_avatar"}` — bad `avatar_id`.
- `402 {"error":"locked","reason":"min_spend"}` — free interactions used up →
  **show the unlock/paywall screen instead of connecting.**
- `401` — bad/missing token.

Keep `session_id` and `bot_url`; both are needed next.

```bash
curl -sS -X POST "https://innocent-swine-roughly.ngrok-free.app/voice-avatars/match/" \
  -H "JWT-Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"avatar_id": 1}'
```

---

## 3. Start the voice call (React Native + WebRTC)

This is **not** a REST call — it's a live audio (WebRTC) connection to `bot_url`. The bot
handles speech-to-text, the AI, text-to-speech, turn-taking and interruptions. You stream
mic audio and play what comes back.

**Install**

```bash
npm i @pipecat-ai/client-js @pipecat-ai/react-native-small-webrtc-transport react-native-webrtc
# iOS: cd ios && pod install
```

**Permissions**

- iOS `Info.plist`: `NSMicrophoneUsageDescription` (mic usage string).
- Android `AndroidManifest.xml`: `<uses-permission android:name="android.permission.RECORD_AUDIO" />`
  and request it at runtime before connecting.

**Connect**

```ts
import { PipecatClient } from "@pipecat-ai/client-js";
import { RNSmallWebRTCTransport } from "@pipecat-ai/react-native-small-webrtc-transport";

// bot_url + session_id come from the Match response (§2).
// Pass session_id as a query param — the bot reads it from there.
const connectionUrl = `${bot_url}?session_id=${session_id}`;

const client = new PipecatClient({
  transport: new RNSmallWebRTCTransport({
    connectionUrl,
    // Same TURN as the backend — required for cellular/NAT (see below).
    iceServers: [
      { urls: "stun:stun.l.google.com:19302" },
      {
        urls: ["turn:standard.relay.metered.ca:80", "turns:standard.relay.metered.ca:443"],
        username: "<TURN_USERNAME>",
        credential: "<TURN_CREDENTIAL>",
      },
    ],
  }),
  enableMic: true,
  enableCam: false,
});

client.on("botStartedSpeaking", () => setState("avatar_speaking"));
client.on("userStartedSpeaking", () => setState("listening")); // barge-in
client.on("disconnected", () => endCall());

await client.connect();      // asks for mic permission
// ...on hang up:
await client.disconnect();
```

> The **raw signaling shape** (what the SDK does under the hood) is `POST {bot_url}` with
> `{ sdp, type: "offer", session_id }` → `{ sdp, type: "answer", pc_id }`. A working
> browser reference is `testclient/index.html` if you need to see the exact protocol.

**Drive the call UI** from the events: connecting → listening (user speaking) →
avatar_speaking → ended. Talking over the avatar interrupts it (barge-in is automatic).
When the user hangs up: `disconnect()`, then call End (§4).

### ⚠️ Two backend requirements for mobile (ask backend)

1. **Public `bot_url`.** A phone can't reach `localhost`. The bot must be exposed at a
   public HTTPS URL, and `VOICE_BOT_URL` set to it so Match returns a reachable value.
2. **TURN server.** ngrok tunnels only the *signaling*, not the audio. On cellular/NAT the
   phone and bot can't connect peer-to-peer with STUN alone → **call connects but no
   audio**. A TURN server (same creds on client `iceServers` above **and** the backend's
   `VOICE_TURN_*`) fixes this. Free creds: create a project at metered.ca.

---

## 4. End call (on hang-up)

**Send**

| | |
|---|---|
| Method | `POST` |
| Path | `/voice-avatars/{session_id}/end/` |
| Headers | `JWT-Authorization: Bearer <token>`, `Content-Type: application/json` |
| Body | `{ "duration_seconds": 72 }`  ← elapsed call time |

**Get back — `200 OK`**

```json
{ "duration_seconds": 72, "next_locked": false }
```

`next_locked: true` means the *next* Match will return `402` (show the unlock screen then).

**Errors:** `404 {"error":"not_found"}` (unknown session), `401`.

```bash
curl -sS -X POST "https://innocent-swine-roughly.ngrok-free.app/voice-avatars/<session_id>/end/" \
  -H "JWT-Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"duration_seconds": 72}'
```

---

## End-to-end flow

```
GET /avatars ──> render deck
   │ left swipe ─> next card (no call)
   │ right swipe
   ▼
POST /match {avatar_id}
   │ 402 locked ─> show unlock screen (stop here)
   │ 201 -> { session_id, bot_url }
   ▼
WebRTC connect to bot_url?session_id=…  ──> live voice call (mic in / audio out)
   │ user hangs up
   ▼
POST /{session_id}/end {duration_seconds}
```

## Quick reference

| Step | Method | Path | Send | Success |
|------|--------|------|------|---------|
| Avatars | GET | `/voice-avatars/avatars/` | — | `200 { avatars: Avatar[] }` |
| Match | POST | `/voice-avatars/match/` | `{ avatar_id }` | `201 { session_id, avatar, bot_url }` / `402 locked` |
| Call | — | WebRTC → `bot_url?session_id=` | SDP offer | audio call |
| End | POST | `/voice-avatars/{session_id}/end/` | `{ duration_seconds }` | `200 { duration_seconds, next_locked }` |

## Gotchas checklist

- [ ] Auth header is **`JWT-Authorization: Bearer <token>`** (not `Authorization`).
- [ ] Handle **`402`** on Match → unlock screen.
- [ ] Request **mic permission** (iOS `NSMicrophoneUsageDescription` / Android `RECORD_AUDIO`) before connecting.
- [ ] Pass **`session_id`** to the bot (query param `?session_id=…`).
- [ ] `bot_url` comes **from Match**, never hardcode it — and it must be a **public** URL for the phone.
- [ ] **TURN server** configured on client `iceServers` (mobile has no audio without it).
- [ ] Response fields are **snake_case**.

"""Pipecat voice agent for swipe-to-talk avatars.

Standalone service — no Django import. Talks to the Avatars API over HTTP for
private personas, and serves WebRTC signaling on :7860.

Run from this directory or repo root::

    python voice_agent/agent.py
    # or
    cd voice_agent && python agent.py
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load repo-root .env first, then voice_agent/.env (overrides).
_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
load_dotenv(_REPO / ".env")
load_dotenv(_HERE / ".env", override=True)

import httpx  # noqa: E402
from aiohttp import web  # noqa: E402
from pipecat.audio.vad.silero import SileroVADAnalyzer  # noqa: E402
from pipecat.pipeline.pipeline import Pipeline  # noqa: E402
from pipecat.pipeline.worker import PipelineParams, PipelineWorker  # noqa: E402
from pipecat.processors.aggregators.llm_context import LLMContext  # noqa: E402
from pipecat.processors.aggregators.llm_response_universal import (  # noqa: E402
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.cartesia.tts import CartesiaTTSService  # noqa: E402
from pipecat.services.deepgram.stt import DeepgramSTTService  # noqa: E402
from pipecat.services.openrouter.llm import OpenRouterLLMService  # noqa: E402
from pipecat.transports.base_transport import TransportParams  # noqa: E402
from pipecat.transports.smallwebrtc.connection import (  # noqa: E402
    IceServer,
    SmallWebRTCConnection,
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport  # noqa: E402
from pipecat.workers.runner import WorkerRunner  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_agent")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _env_list(name: str) -> list[str]:
    raw = _env(name, "")
    if not raw.strip():
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


DJANGO_URL = _env("VOICE_DJANGO_URL", "http://localhost:8000").rstrip("/")
BOT_AUTH_KEY = _env("VOICE_BOT_AUTH_KEY", "dev-bot-key")
LLM_MODEL = _env("VOICE_LLM_MODEL", "google/gemini-2.5-flash")
PORT = int(_env("VOICE_BOT_PORT", "7860"))
OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY")
DEEPGRAM_API_KEY = _env("DEEPGRAM_API_KEY")
CARTESIA_API_KEY = _env("CARTESIA_API_KEY")
TURN_URLS = _env_list("VOICE_TURN_URLS")
TURN_USERNAME = _env("VOICE_TURN_USERNAME") or None
TURN_CREDENTIAL = _env("VOICE_TURN_CREDENTIAL") or None

ICE_SERVERS = [IceServer(urls="stun:stun.l.google.com:19302")]
if TURN_URLS:
    ICE_SERVERS.append(
        IceServer(urls=TURN_URLS, username=TURN_USERNAME, credential=TURN_CREDENTIAL)
    )

_connections: dict[str, SmallWebRTCConnection] = {}


async def fetch_persona(session_id: str) -> dict:
    """Fetch the private persona for a session from the Avatars API."""
    url = f"{DJANGO_URL}/voice-avatars/{session_id}/internal/"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers={"x-voice-bot-key": BOT_AUTH_KEY})
        resp.raise_for_status()
        return resp.json()


async def run_bot(connection: SmallWebRTCConnection, session_id: str) -> None:
    """Build and run the voice pipeline for one WebRTC connection."""
    try:
        persona = await fetch_persona(session_id)
    except Exception:  # noqa: BLE001
        logger.exception("persona_fetch_failed", extra={"session_id": session_id})
        await connection.disconnect()
        return

    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )

    stt = DeepgramSTTService(
        api_key=DEEPGRAM_API_KEY,
        settings=DeepgramSTTService.Settings(
            model="nova-2-general",
            language=persona.get("lang", "en"),
            smart_format=True,
        ),
    )
    llm = OpenRouterLLMService(
        api_key=OPENROUTER_API_KEY,
        settings=OpenRouterLLMService.Settings(model=LLM_MODEL),
    )
    tts = CartesiaTTSService(
        api_key=CARTESIA_API_KEY,
        settings=CartesiaTTSService.Settings(model="sonic-3.5", voice=persona["voice_id"]),
    )

    context = LLMContext(
        messages=[
            {"role": "system", "content": persona["system_prompt"]},
            {"role": "assistant", "content": persona["first_message"]},
        ]
    )
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    logger.info("voice_agent_started", extra={"session_id": session_id})
    await runner.run()
    logger.info("voice_agent_finished", extra={"session_id": session_id})


async def offer(request: web.Request) -> web.Response:
    """WebRTC signaling endpoint the browser POSTs its SDP to."""
    body = await request.json()
    session_id = body.get("session_id") or request.query.get("session_id")
    if not session_id:
        return web.json_response({"error": "missing session_id"}, status=400)

    pc_id = body.get("pc_id")
    if pc_id and pc_id in _connections:
        connection = _connections[pc_id]
        await connection.renegotiate(sdp=body["sdp"], type=body["type"])
    else:
        connection = SmallWebRTCConnection(ice_servers=ICE_SERVERS)
        await connection.initialize(sdp=body["sdp"], type=body["type"])

        @connection.event_handler("closed")
        async def _on_closed(conn: SmallWebRTCConnection) -> None:
            _connections.pop(conn.pc_id, None)

        _connections[connection.pc_id] = connection
        asyncio.create_task(run_bot(connection, session_id))

    answer = connection.get_answer()
    return web.json_response(answer)


@web.middleware
async def cors_middleware(request: web.Request, handler):
    """Permissive CORS for the browser test client (dev)."""
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def main() -> None:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_post("/voice-agent/connect", offer)
    app.router.add_get("/health", health)
    logger.info("voice agent listening on :%s (POST /voice-agent/connect)", PORT)
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()

"""
webhook/server.py — FastAPI webhook server for Telnyx SMS + Call forwarding
Handles:
  POST /webhook/sms      → inbound SMS → Telegram notify + optional MY forward
  POST /texml/forward    → inbound call → TeXML forward to MY number
  POST /texml/voicemail  → inbound call → TeXML voicemail
  GET  /health           → health check
"""

import os
import json
import logging
import hmac
import hashlib
import requests
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telnyx-webhook")

app = FastAPI(title="Telnyx Tools Webhook", version="1.0.0")

# ─── Config from env ──────────────────────────────────────────────────────────

TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY", "")
TELNYX_PUBLIC_KEY = os.environ.get("TELNYX_PUBLIC_KEY", "")  # for webhook signature verification
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_OWNER_CHAT_ID = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "8226870570")  # Jewel
TELEGRAM_RELAY_CHAT_ID = os.environ.get("TELEGRAM_RELAY_CHAT_ID", "")  # team member
FORWARD_TO_NUMBER = os.environ.get("FORWARD_TO_NUMBER", "+601121113249")  # MY number
TELNYX_FROM_NUMBER = os.environ.get("TELNYX_FROM_NUMBER", "+13079999692")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def send_telegram(chat_id: str, text: str):
    """Fire a Telegram message."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        logger.warning("Telegram not configured")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=8,
        )
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


def forward_sms_to_number(to: str, text: str, original_from: str):
    """Forward an inbound SMS to a phone number via Telnyx."""
    try:
        requests.post(
            "https://api.telnyx.com/v2/messages",
            json={
                "from": TELNYX_FROM_NUMBER,
                "to": to,
                "text": f"[Fwd from {original_from}]: {text}"
            },
            headers={"Authorization": f"Bearer {TELNYX_API_KEY}"},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"SMS forward failed: {e}")


def build_forward_texml(to_number: str, whisper: str = None) -> str:
    whisper_tag = f"<Say>{whisper}</Say>" if whisper else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  {whisper_tag}
  <Dial timeout="30">
    <Number>{to_number}</Number>
  </Dial>
</Response>"""


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "telnyx-tools-webhook"}


@app.post("/webhook/sms")
async def inbound_sms(request: Request):
    """Handle inbound SMS from Telnyx."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    data = body.get("data", {}).get("payload", {})
    event_type = body.get("data", {}).get("event_type", "")

    if "message" not in event_type:
        return {"received": True}

    from_number = data.get("from", {}).get("phone_number", "unknown")
    to_numbers = [t.get("phone_number") for t in data.get("to", [])]
    text = data.get("text", "")
    direction = data.get("direction", "inbound")

    logger.info(f"SMS [{direction}] from={from_number} to={to_numbers} text={text[:50]}")

    if direction == "inbound":
        # 1. Notify owner on Telegram
        notif = (
            f"📩 <b>Inbound SMS</b>\n"
            f"From: <code>{from_number}</code>\n"
            f"To: <code>{', '.join(to_numbers)}</code>\n"
            f"Message: {text}"
        )
        send_telegram(TELEGRAM_OWNER_CHAT_ID, notif)

        # 2. If relay is configured, also notify the team member
        if TELEGRAM_RELAY_CHAT_ID:
            relay_msg = f"📱 SMS from <code>{from_number}</code>:\n{text}\n\n<i>Reply here to respond via SMS</i>"
            send_telegram(TELEGRAM_RELAY_CHAT_ID, relay_msg)

    return {"received": True}


@app.post("/texml/forward")
async def texml_forward(request: Request):
    """Return TeXML to forward inbound call to MY number."""
    from_num = request.query_params.get("From", "unknown")
    to_num = request.query_params.get("To", "unknown")
    logger.info(f"Inbound call: from={from_num} to={to_num} → forwarding to {FORWARD_TO_NUMBER}")

    # Notify on Telegram
    send_telegram(
        TELEGRAM_OWNER_CHAT_ID,
        f"📞 <b>Inbound Call</b>\nFrom: <code>{from_num}</code>\nTo: <code>{to_num}</code>\nForwarding to: <code>{FORWARD_TO_NUMBER}</code>"
    )

    texml = build_forward_texml(
        FORWARD_TO_NUMBER,
        whisper=f"Forwarded call from {from_num}"
    )
    return Response(content=texml, media_type="application/xml")


@app.post("/texml/voicemail")
async def texml_voicemail(request: Request):
    """Return TeXML for voicemail when no answer."""
    from_num = request.query_params.get("From", "unknown")
    texml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Hi, you've reached W3J. Please leave a message after the beep and we'll get back to you shortly.</Say>
  <Record maxLength="120" transcribe="true" transcribeCallback="/webhook/voicemail-transcript" />
</Response>"""
    return Response(content=texml, media_type="application/xml")


@app.post("/webhook/voicemail-transcript")
async def voicemail_transcript(request: Request):
    """Handle transcribed voicemail."""
    form = await request.form()
    transcript = form.get("TranscriptionText", "No transcript")
    recording_url = form.get("RecordingUrl", "")
    caller = form.get("From", "unknown")

    send_telegram(
        TELEGRAM_OWNER_CHAT_ID,
        f"📬 <b>Voicemail</b>\nFrom: <code>{caller}</code>\nTranscript: {transcript}\n🔗 {recording_url}"
    )
    return {"received": True}


@app.post("/relay/telegram-to-sms")
async def telegram_relay(request: Request):
    """
    Telegram webhook → send SMS reply.
    Wire your team member's bot to POST here.
    Body: { "from": "+13079999692", "to": "+60112345678", "text": "message" }
    """
    body = await request.json()
    from_num = body.get("from", TELNYX_FROM_NUMBER)
    to_num = body.get("to")
    text = body.get("text", "")

    if not to_num or not text:
        raise HTTPException(status_code=400, detail="Missing to or text")

    resp = requests.post(
        "https://api.telnyx.com/v2/messages",
        json={"from": from_num, "to": to_num, "text": text},
        headers={"Authorization": f"Bearer {TELNYX_API_KEY}"},
        timeout=10,
    )
    return {"success": resp.ok, "status_code": resp.status_code}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

"""
call_tool.py — Hermes + OpenClaw tool definitions for call forwarding
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.telnyx_client import TelnyxClient

_client = None

def _get_client() -> TelnyxClient:
    global _client
    if not _client:
        _client = TelnyxClient()
    return _client


# ── TeXML generator ───────────────────────────────────────────────────────────

def build_forward_texml(to_number: str, whisper: str = None) -> str:
    """Generate TeXML to forward a call to a number."""
    whisper_tag = ""
    if whisper:
        whisper_tag = f'<Say>{whisper}</Say>'
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  {whisper_tag}
  <Dial timeout="30" record="false">
    <Number>{to_number}</Number>
  </Dial>
</Response>"""


def build_voicemail_texml(greeting: str = None) -> str:
    """Generate TeXML to record a voicemail."""
    msg = greeting or "Please leave a message after the beep."
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>{msg}</Say>
  <Record maxLength="120" transcribe="true" />
</Response>"""


# ── Tool: forward_call ────────────────────────────────────────────────────────

TOOL_FORWARD_CALL = {
    "name": "forward_call",
    "description": (
        "Configure call forwarding for a Telnyx number. "
        "Routes all inbound calls to a destination number (e.g. your Malaysian mobile). "
        "Uses TeXML webhook — call the /texml/forward endpoint."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "from_number": {
                "type": "string",
                "description": "The Telnyx number to configure forwarding on"
            },
            "to_number": {
                "type": "string",
                "description": "Destination number in E.164 format, e.g. +601121113249"
            },
            "whisper": {
                "type": "string",
                "description": "Optional message to say before connecting (e.g. 'Forwarded from Bold Connect')"
            }
        },
        "required": ["from_number", "to_number"]
    }
}

def forward_call(from_number: str, to_number: str, whisper: str = None) -> dict:
    """Configure TeXML forwarding for a number."""
    texml = build_forward_texml(to_number, whisper)
    # Return the TeXML — this is served by the webhook server
    # The actual wiring happens when the TeXML app is assigned to the number
    return {
        "success": True,
        "action": "forward_configured",
        "from": from_number,
        "to": to_number,
        "texml": texml,
        "note": "TeXML app must be assigned to the number via Telnyx portal or webhook server."
    }


# ── Hermes tool manifest ──────────────────────────────────────────────────────

HERMES_TOOLS = [TOOL_FORWARD_CALL]

TOOL_HANDLERS = {
    "forward_call": forward_call,
}

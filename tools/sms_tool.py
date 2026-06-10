"""
sms_tool.py — Hermes + OpenClaw tool definitions for SMS
Drop into any Hermes agent tools/ directory.
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


# ── Tool: send_sms ────────────────────────────────────────────────────────────

TOOL_SEND_SMS = {
    "name": "send_sms",
    "description": (
        "Send an SMS message via Telnyx to any phone number. "
        "Use for recruitment outreach, team notifications, or customer messages. "
        "Default from_number is the recruitment line (+13079999692)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient phone number in E.164 format, e.g. +60112345678"
            },
            "message": {
                "type": "string",
                "description": "The SMS message text to send"
            },
            "from_number": {
                "type": "string",
                "description": "Telnyx number to send from. Defaults to TELNYX_FROM_NUMBER env var.",
                "default": "+13079999692"
            }
        },
        "required": ["to", "message"]
    }
}

def send_sms(to: str, message: str, from_number: str = None) -> dict:
    """Execute the send_sms tool."""
    client = _get_client()
    result = client.send_sms(to=to, text=message, from_number=from_number)
    msg = result.get("data", {})
    return {
        "success": True,
        "message_id": msg.get("id"),
        "status": msg.get("to", [{}])[0].get("status", "queued") if msg.get("to") else "queued",
        "to": to,
        "from": msg.get("from", {}).get("phone_number"),
        "cost": msg.get("cost", {}).get("amount"),
    }


# ── Tool: list_sms ────────────────────────────────────────────────────────────

TOOL_LIST_SMS = {
    "name": "list_sms",
    "description": (
        "List recent SMS messages sent/received on the Telnyx account. "
        "Use to check if a message was delivered or to review conversation history."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of messages to return (default 10)",
                "default": 10
            },
            "direction": {
                "type": "string",
                "enum": ["inbound", "outbound"],
                "description": "Filter by direction"
            }
        }
    }
}

def list_sms(limit: int = 10, direction: str = None) -> dict:
    """Execute the list_sms tool."""
    client = _get_client()
    messages = client.list_messages(page_size=limit)
    result = []
    for m in messages:
        frm = m.get("from", {}).get("phone_number", "?")
        tos = [t.get("phone_number") for t in m.get("to", [])]
        result.append({
            "id": m.get("id"),
            "direction": m.get("direction"),
            "from": frm,
            "to": tos,
            "text": m.get("text", "")[:200],
            "status": m.get("to", [{}])[0].get("status") if m.get("to") else m.get("direction"),
            "received_at": m.get("received_at") or m.get("created_at", ""),
        })
    if direction:
        result = [m for m in result if m.get("direction") == direction]
    return {"messages": result[:limit], "total": len(result)}


# ── Tool: list_numbers ────────────────────────────────────────────────────────

TOOL_LIST_NUMBERS = {
    "name": "list_telnyx_numbers",
    "description": "List all Telnyx phone numbers on the account with their current config.",
    "parameters": {"type": "object", "properties": {}}
}

def list_numbers() -> dict:
    client = _get_client()
    nums = client.list_numbers()
    return {
        "numbers": [
            {
                "number": n["phone_number"],
                "status": n.get("status"),
                "connection": n.get("connection_name"),
                "messaging_profile": n.get("messaging_profile_id"),
                "call_forwarding": n.get("call_forwarding_enabled"),
            }
            for n in nums
        ]
    }


# ── Hermes tool manifest ───────────────────────────────────────────────────────

HERMES_TOOLS = [TOOL_SEND_SMS, TOOL_LIST_SMS, TOOL_LIST_NUMBERS]

TOOL_HANDLERS = {
    "send_sms": send_sms,
    "list_sms": list_sms,
    "list_telnyx_numbers": list_numbers,
}

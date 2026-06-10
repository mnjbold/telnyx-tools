"""
telnyx_client.py — Core Telnyx API wrapper
Hermes / OpenClaw compatible. Zero vendor lock-in beyond env vars.
"""

import os
import requests
from typing import Optional, List, Dict, Any


class TelnyxClient:
    BASE_URL = "https://api.telnyx.com/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ["TELNYX_API_KEY"]
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _get(self, path: str, params: dict = None) -> dict:
        r = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> dict:
        r = self.session.post(f"{self.BASE_URL}{path}", json=data, timeout=15)
        r.raise_for_status()
        return r.json()

    def _patch(self, path: str, data: dict) -> dict:
        r = self.session.patch(f"{self.BASE_URL}{path}", json=data, timeout=15)
        r.raise_for_status()
        return r.json()

    # ─── SMS ──────────────────────────────────────────────────────────────────

    def send_sms(
        self,
        to: str,
        text: str,
        from_number: Optional[str] = None,
        messaging_profile_id: Optional[str] = None,
    ) -> dict:
        """Send an SMS via Telnyx."""
        from_num = from_number or os.environ.get("TELNYX_FROM_NUMBER", "+13079999692")
        payload: Dict[str, Any] = {"from": from_num, "to": to, "text": text}
        if messaging_profile_id:
            payload["messaging_profile_id"] = messaging_profile_id
        return self._post("/messages", payload)

    def list_messages(self, page_size: int = 20, status: Optional[str] = None) -> List[dict]:
        """List recent messages."""
        params = {"page[size]": page_size}
        if status:
            params["filter[status]"] = status
        data = self._get("/messages", params)
        return data.get("data", [])

    def get_message(self, message_id: str) -> dict:
        """Get a specific message by ID."""
        return self._get(f"/messages/{message_id}").get("data", {})

    # ─── Phone Numbers ────────────────────────────────────────────────────────

    def list_numbers(self) -> List[dict]:
        """List all phone numbers on the account."""
        data = self._get("/phone_numbers")
        return data.get("data", [])

    def get_number(self, number: str) -> Optional[dict]:
        """Get config for a specific number."""
        nums = self.list_numbers()
        return next((n for n in nums if n["phone_number"] == number), None)

    def assign_messaging_profile(self, number_id: str, profile_id: str) -> dict:
        """Assign a messaging profile to a phone number."""
        return self._patch(f"/phone_numbers/{number_id}", {
            "messaging_profile_id": profile_id
        })

    # ─── Messaging Profiles ──────────────────────────────────────────────────

    def list_messaging_profiles(self) -> List[dict]:
        data = self._get("/messaging_profiles")
        return data.get("data", [])

    def create_messaging_profile(self, name: str, webhook_url: str) -> dict:
        return self._post("/messaging_profiles", {
            "name": name,
            "webhook_url": webhook_url,
            "webhook_failover_url": "",
            "enabled": True,
        })

    def update_messaging_profile_webhook(self, profile_id: str, webhook_url: str) -> dict:
        return self._patch(f"/messaging_profiles/{profile_id}", {
            "webhook_url": webhook_url
        })

    # ─── TeXML / Call Forwarding ──────────────────────────────────────────────

    def list_texml_apps(self) -> List[dict]:
        data = self._get("/texml_applications")
        return data.get("data", [])

    def create_forward_app(self, name: str, webhook_url: str) -> dict:
        """Create a TeXML app that handles inbound calls via webhook."""
        return self._post("/texml_applications", {
            "friendly_name": name,
            "inbound": {
                "webhook_url": webhook_url,
                "webhook_url_method": "POST",
                "channel_limit": 10,
            },
            "outbound": {
                "outbound_voice_profile_id": None
            }
        })

    def assign_texml_app(self, number_id: str, app_id: str) -> dict:
        """Assign a TeXML app (voice connection) to a phone number."""
        return self._patch(f"/phone_numbers/{number_id}", {
            "connection_id": app_id
        })

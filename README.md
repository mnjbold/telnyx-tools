# telnyx-tools

Plug-and-play Telnyx SMS & Voice toolkit.  
Works as **Hermes agent tools**, **OpenClaw skills**, or standalone Python/Node library.

## Features

- 📤 Send SMS from any Telnyx number
- 📥 Receive SMS via webhook → forward to Telegram / callback
- 📞 Call forwarding (inbound → any number via TeXML)
- 🔁 SMS relay for non-technical team members via Telegram bot
- 🛠️ Hermes tool definitions (JSON schema compatible)
- 🦾 OpenClaw skill definitions

## Quickstart

```bash
pip install -r requirements.txt

export TELNYX_API_KEY=KEYxxx
export TELNYX_FROM_NUMBER=+13079999692
export TELEGRAM_BOT_TOKEN=xxx
export TELEGRAM_CHAT_ID=your_chat_id
export FORWARD_TO_NUMBER=+601121113249   # your MY number

python src/server.py
```

## Architecture

```
Inbound SMS → Telnyx webhook → /webhook/sms → 
    → forward to Telegram (instant notify)
    → optionally forward to MY number via SMS

Outbound SMS → Hermes tool call → send_sms() → Telnyx API

Call Forwarding → Telnyx TeXML app → forward_call TeXML → MY number
```

## Numbers

| Number | Role | SMS | Voice |
|--------|------|-----|-------|
| +13079999692 | Recruitment / General | ✅ | ✅ |
| +13204280793 | Bold Connect / Retell | ✅ | ✅ |
| +18444618814 | Operator Forward | ❌ | ✅ |

## Hermes Tool Usage

```python
from tools.sms_tool import send_sms, get_messages
from tools.call_tool import forward_call, make_call

# Send SMS
send_sms(to="+60112345678", message="Hi from W3J!", from_number="+13079999692")

# Forward all inbound calls to MY number
forward_call(to="+601121113249")
```

## OpenClaw Integration

```yaml
# openclaw/skills/telnyx.yaml
name: telnyx
description: Send SMS, receive messages, forward calls via Telnyx
entrypoint: skills/telnyx_skill.py
env_required:
  - TELNYX_API_KEY
  - TELNYX_FROM_NUMBER
tools:
  - send_sms
  - list_messages
  - forward_call
  - relay_agent
```

## Team Member SMS Access (Non-Technical)

Set `RELAY_TELEGRAM_CHAT_ID` to your team member's Telegram chat ID.  
They just message the bot — the agent relays to/from the Telnyx number.

```
Team member → Telegram bot → MAVEN/relay agent → Telnyx SMS → Candidate
Candidate reply → Telnyx webhook → relay agent → Telegram to team member
```

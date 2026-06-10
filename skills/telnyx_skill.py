"""
skills/telnyx_skill.py — OpenClaw / Hermes skill entrypoint
Usage: python telnyx_skill.py <tool_name> [json_args]

Example:
    python telnyx_skill.py send_sms '{"to": "+60112345678", "message": "Hello!"}'
    python telnyx_skill.py list_sms '{"limit": 5}'
    python telnyx_skill.py list_telnyx_numbers '{}'
"""

import os
import sys
import json

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.sms_tool import TOOL_HANDLERS as SMS_HANDLERS, HERMES_TOOLS as SMS_TOOLS
from tools.call_tool import TOOL_HANDLERS as CALL_HANDLERS, HERMES_TOOLS as CALL_TOOLS

ALL_HANDLERS = {**SMS_HANDLERS, **CALL_HANDLERS}
ALL_TOOLS = SMS_TOOLS + CALL_TOOLS


def main():
    if len(sys.argv) < 2:
        print("Available tools:")
        for t in ALL_TOOLS:
            print(f"  {t['name']}: {t['description'][:80]}")
        sys.exit(0)

    tool_name = sys.argv[1]
    args_raw = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        args = json.loads(args_raw)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON args: {e}", file=sys.stderr)
        sys.exit(1)

    handler = ALL_HANDLERS.get(tool_name)
    if not handler:
        print(f"Error: unknown tool '{tool_name}'", file=sys.stderr)
        print(f"Available: {list(ALL_HANDLERS.keys())}", file=sys.stderr)
        sys.exit(1)

    try:
        result = handler(**args)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e), "tool": tool_name}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

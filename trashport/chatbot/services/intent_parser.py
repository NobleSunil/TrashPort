import json

def parse_response(raw: str) -> dict:
    """
    Parses the raw response from the LLM, validating its type and action format.
    """
    raw = raw.strip()
    # Strip markdown code block formatting if present
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                return {"type": "text", "message": raw}
        else:
            return {"type": "text", "message": raw}

    if not isinstance(parsed, dict):
        return {"type": "text", "message": "I can only help with TrashPort-related questions."}

    response_type = parsed.get("type")
    valid_types = {"text", "redirect", "ask", "action_done", "action", "greeting"}
    if response_type not in valid_types:
        return {"type": "text", "message": "I can only help with TrashPort-related questions."}

    if response_type == "action":
        action = parsed.get("action")
        valid_actions = {"book_pickup", "edit_pickup", "cancel_pickup", "check_status"}
        if action not in valid_actions:
            return {"type": "text", "message": "I can only help with TrashPort-related questions."}

    return parsed

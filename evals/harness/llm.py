"""Thin Anthropic Messages API wrapper.

Every judge and runner call goes through here, so model IDs, JSON handling, and
error messages stay consistent. The `anthropic` package is imported lazily so the
rest of the harness (dataset loading, harvesting) works without it installed.
"""
import json
import re

_client = None


def _client_singleton():
    global _client
    if _client is None:
        try:
            import anthropic
        except ImportError:
            raise SystemExit(
                "The 'anthropic' package is required for run/score/compare.\n"
                "Install it: pip install -r evals/requirements.txt"
            )
        try:
            _client = anthropic.Anthropic()
        except Exception as exc:  # noqa: BLE001 — surface any construction failure clearly
            raise SystemExit(
                f"Could not construct the Anthropic client: {exc}\n"
                "Set ANTHROPIC_API_KEY, or run `ant auth login`."
            )
    return _client


def _extract_json(text):
    """Parse a JSON object out of a model response, tolerating stray fences/prose."""
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            return json.loads(text[start:end + 1])
        raise


def complete_json(system, user, schema, model, max_tokens=4000):
    """Call `model` and return a parsed JSON object conforming to `schema`.

    Uses structured outputs (`output_config.format`) when the SDK/model support it,
    and falls back to a prompt instruction + tolerant parsing otherwise.
    """
    client = _client_singleton()   # friendly SystemExit if anthropic is missing
    import anthropic               # safe: _client_singleton already imported it

    system = (
        system
        + "\n\nRespond with ONLY a JSON object conforming to this JSON schema — "
        "no prose, no markdown fences:\n" + json.dumps(schema)
    )
    base = dict(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    try:
        resp = client.messages.create(
            output_config={"format": {"type": "json_schema", "schema": schema}}, **base
        )
    except (TypeError, anthropic.BadRequestError):
        # SDK too old for output_config, or the model rejected the schema —
        # fall back to the prompt instruction embedded in `system`.
        resp = client.messages.create(**base)
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
    return _extract_json(text)

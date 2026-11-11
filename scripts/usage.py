"""Token usage and API-equivalent cost of one Harbor trial, from the agent's raw logs.

Both arms are priced with the same table, from the tokens each harness actually sent,
rather than trusting either harness's own cost estimate. Runs use a Claude subscription,
so these are API-equivalent dollars, not a bill.

Claude Code: when its stream-json output (`agent/claude-code.txt`) ends with a `result`
event, that event's `modelUsage` is used (it also covers side calls such as Haiku).
Otherwise (a run killed at its timeout) usage is the sum, per message id, of the final
usage recorded in Claude Code's session transcripts (`agent/sessions/projects/**/*.jsonl`),
which is also kept as a cross-check on finished runs. The stream's own assistant events
are not used for counting: they carry each message's usage from its start, without the
output (and thinking) tokens. Server-side web searches are priced at $10 per 1,000.

nanocode: every Messages request is a `model.call` span (compaction a
`model.compaction` span, prompt-cache keep-alive a `claude.cache.refresh` span) in its local OpenTelemetry traces
(`agent/nanocode-home/log/otel/*/traces.jsonl`). nanocode's `input_tokens` is
cache-inclusive, so uncached input = input - cache reads - cache writes. Its prompt cache
is written with a 1-hour TTL, as is Claude Code's under OAuth (verified on captures).

`model_calls` is the number of Messages API responses in both arms, subagents included.
"""

import json
import sys
from pathlib import Path

# USD per million tokens: input, output, cache read, cache write 5m, cache write 1h.
# Claude API list prices; cache writes at 1.25x (5m) and 2x (1h) input.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00, 8.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.10, 2.50, 4.00),
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125, 0.20),
    "claude-haiku-4-5": (1.00, 5.00, 0.10, 1.25, 2.00),
    "claude-opus-5": (5.00, 25.00, 0.50, 6.25, 10.00),
    "claude-opus-4-8": (5.00, 25.00, 0.50, 6.25, 10.00),
}
FALLBACK = PRICES["claude-opus-5-5"]
WEB_SEARCH_USD = 0.01
KEYS = ("uncached_input", "output", "cache_read", "cache_write_5m", "cache_write_1h")


def price(model: str) -> tuple[tuple[float, ...], bool]:
    """Price row for a model id, and whether the fallback (Opus 5.5) was used."""
    if model == "<synthetic>":  # Claude Code's locally generated messages (e.g. API errors)
        return (0.0,) * 5, False
    for name in sorted(PRICES, key=len, reverse=True):
        if model.startswith(name):
            return PRICES[name], False
    print(f"usage: no price for {model!r}; priced at Opus 5.5 rates", file=sys.stderr)
    return FALLBACK, True


def _empty() -> dict:
    return {**{k: 0 for k in KEYS}, "model_calls": 0, "web_searches": 0, "api_retries": 0,
            "models": {}, "priced_by_fallback": False}


def _add(usage: dict, model: str, **counts: int) -> None:
    per_model = usage["models"].setdefault(model, {k: 0 for k in KEYS})
    for key, value in counts.items():
        usage[key] += value
        per_model[key] += value


def cost(usage: dict) -> float:
    total = usage.get("web_searches", 0) * WEB_SEARCH_USD
    for model, u in usage["models"].items():
        p, fallback = price(model)
        usage["priced_by_fallback"] |= fallback
        total += sum(u[k] * rate for k, rate in zip(KEYS, p)) / 1e6
    return total


def _events(path: Path):
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def _transcript_messages(agent_dir: Path) -> dict:
    """Final usage of every assistant message in Claude Code's session transcripts
    (main loop and subagents), by message id. Unlike stream-json events, which carry
    the usage snapshot from the start of a message, the transcript holds final counts
    (they matched `result.modelUsage` exactly on every calibration trial)."""
    messages = {}
    for path in sorted((agent_dir / "sessions").glob("projects/**/*.jsonl")):
        for event in _events(path):
            message = event.get("message")
            if (isinstance(message, dict) and message.get("role") == "assistant" and message.get("id")
                    and message.get("usage") and message.get("model") != "<synthetic>"):
                messages[message["id"]] = (message.get("model", "unknown"), message["usage"])
    return messages


def claude_code_usage(agent_dir: Path) -> dict | None:
    stream = agent_dir / "claude-code.txt"
    if not stream.is_file():
        return None
    result, retries = None, 0
    for event in _events(stream):
        kind = event.get("type")
        if kind == "result":
            result = event
        elif kind == "system" and "retry" in str(event.get("subtype", "")):
            retries += 1
    messages = _transcript_messages(agent_dir)

    from_events = _empty()
    for model, u in messages.values():
        creation = u.get("cache_creation") or {}
        writes = u.get("cache_creation_input_tokens", 0) or 0
        w1h = creation.get("ephemeral_1h_input_tokens", 0) or 0
        _add(from_events, model,
             uncached_input=u.get("input_tokens", 0) or 0,
             output=u.get("output_tokens", 0) or 0,
             cache_read=u.get("cache_read_input_tokens", 0) or 0,
             cache_write_5m=writes - w1h, cache_write_1h=w1h)
        from_events["web_searches"] += (u.get("server_tool_use") or {}).get("web_search_requests", 0) or 0
    from_events["model_calls"] = len(messages)
    from_events["api_retries"] = retries

    status = result.get("api_error_status") if result else None
    if result is None or not result.get("modelUsage"):
        if not messages and status is None:
            return None
        from_events["source"] = "session transcript (no result event)" if result is None else "session transcript"
        from_events["reported_cost_usd"] = None
        from_events["api_error_status"] = status
        return from_events

    usage = _empty()
    for model, u in result["modelUsage"].items():
        writes = u.get("cacheCreationInputTokens", 0)
        w1h = u.get("cacheCreationEphemeral1hInputTokens",
                    round(writes * (from_events["cache_write_1h"]
                                    / max(1, from_events["cache_write_5m"] + from_events["cache_write_1h"]))))
        w1h = min(max(w1h, 0), writes)
        _add(usage, model,
             uncached_input=u.get("inputTokens", 0),
             output=u.get("outputTokens", 0),
             cache_read=u.get("cacheReadInputTokens", 0),
             cache_write_5m=writes - w1h, cache_write_1h=w1h)
        usage["web_searches"] += u.get("webSearchRequests", 0)
    usage["model_calls"] = len(messages)
    usage["api_retries"] = retries
    usage["api_error_status"] = status
    usage["source"] = "result.modelUsage"
    usage["reported_cost_usd"] = result.get("total_cost_usd")
    usage["events_cost_usd"] = cost(from_events)
    return usage


def _value(v: object) -> object:
    return next(iter(v.values())) if isinstance(v, dict) and v else v


def nanocode_usage(agent_dir: Path) -> dict | None:
    traces = sorted((agent_dir / "nanocode-home").glob("log/otel/*/traces.jsonl"))
    if not traces:
        return None
    usage, reported = _empty(), 0.0
    for path in traces:
        for record in _events(path):
            for resource in record.get("resourceSpans", []):
                for scope in resource.get("scopeSpans", []):
                    for span in scope.get("spans", []):
                        a = {x["key"]: _value(x["value"]) for x in span.get("attributes", [])}
                        name = span.get("name")
                        if name in ("model.call", "model.compaction") and "input_tokens" in a:
                            total_in = int(a["input_tokens"])
                            read = int(a.get("cached_input_tokens", 0))
                            write = int(a.get("cache_write_input_tokens", 0))
                            _add(usage, str(a.get("model", "unknown")),
                                 uncached_input=total_in - read - write,
                                 output=int(a.get("output_tokens", 0)),
                                 cache_read=read, cache_write_5m=0, cache_write_1h=write)
                            usage["model_calls"] += 1
                            usage["api_retries"] += max(0, int(a.get("model.attempts", 1)) - 1)
                        elif name == "claude.cache.refresh" and "input_tokens" in a:
                            # keep-alive requests; input_tokens here is not cache-inclusive
                            _add(usage, str(a.get("model", "unknown")),
                                 uncached_input=int(a["input_tokens"]),
                                 output=int(a.get("output_tokens", 0)),
                                 cache_read=int(a.get("cached_input_tokens", 0)),
                                 cache_write_5m=0, cache_write_1h=int(a.get("cache_write_input_tokens", 0)))
                            usage["model_calls"] += 1
                            usage["cache_refreshes"] = usage.get("cache_refreshes", 0) + 1
                        elif name == "agent.turn" and "cost.usd" in a:
                            reported += float(a["cost.usd"])
    usage["source"] = "otel spans"
    usage["reported_cost_usd"] = reported
    return usage


def trial_usage(trial_dir: Path) -> dict | None:
    agent_dir = trial_dir / "agent"
    usage = claude_code_usage(agent_dir) or nanocode_usage(agent_dir)
    if usage is not None:
        usage["cost_usd"] = cost(usage)
        usage["input_total"] = sum(usage[k] for k in KEYS if k != "output")
    return usage

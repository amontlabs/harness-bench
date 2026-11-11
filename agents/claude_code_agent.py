"""Harbor's own claude-code agent, with one addition: stop the harness on timeout.

Harbor enforces the agent timeout with asyncio.wait_for, which cancels run() and kills
only the local `docker exec` client. The `claude` process inside the container keeps
running: it keeps calling the model (spend no log records) and can keep editing files
while the verifier runs. On cancellation this sends SIGKILL to the harness process
only. Processes the agent started on purpose (a server a task asks for) are left alone,
so the verifier sees what the agent left behind. nanocode gets the same treatment.
Everything else, including the command line and environment, is Harbor's.

Error classification also keys on the `api_error_status` of Claude Code's final
`result` event before falling back to Harbor's text patterns, so an API or subscription
limit is classified by status code in this arm as it is in the nanocode arm.
"""

import asyncio
import json
from typing import Any

from harbor.agents.installed.base import (
    AgentAuthenticationError,
    ApiInternalServerError,
    ApiOverloadedError,
    ApiRateLimitError,
    ApiUsageLimitError,
    NonZeroAgentExitCodeError,
)
from harbor.agents.installed.claude_code import ClaudeCode
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

# The native installer's binary is ~/.local/bin/claude; npm's is a node script.
KILL_CLAUDE = (
    "pkill -KILL -x claude 2>/dev/null; "
    # [n] keeps the pattern from matching this very shell command
    "pkill -KILL -f '[n]ode .*claude-code/cli' 2>/dev/null; true"
)


async def stop_harness(environment: BaseEnvironment, kill: str, logs_dir: str) -> None:
    """Kill the harness process; record the process list before and after in the logs."""
    command = (
        f"ps -eo pid,ppid,args > {logs_dir}/timeout-ps-before.txt 2>&1; {kill}; sleep 2; "
        f"ps -eo pid,ppid,args > {logs_dir}/timeout-ps-after.txt 2>&1; true"
    )
    try:
        await asyncio.wait_for(environment.exec(command=command, user="root"), timeout=60)
    except Exception:
        pass


def api_error(status: int, text: str) -> type[NonZeroAgentExitCodeError] | None:
    """Exception class for a failed Messages API status, shared by both arms."""
    if status == 429:
        limit = any(w in text.lower() for w in ("usage limit", "usage_limit", "out of usage"))
        return ApiUsageLimitError if limit else ApiRateLimitError
    if status == 529:
        return ApiOverloadedError
    if status >= 500:
        return ApiInternalServerError
    if status in (401, 403):
        return AgentAuthenticationError
    return None


class ClaudeCodeAgent(ClaudeCode):
    @staticmethod
    def name() -> str:
        return "claude-code"

    def _classify_exec_error(self, command: str, result: Any) -> NonZeroAgentExitCodeError:
        for line in reversed((result.stdout or "").splitlines()):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and event.get("type") == "result":
                try:
                    status = int(event.get("api_error_status") or 0)
                except (TypeError, ValueError):
                    status = 0
                exception = api_error(status, str(event.get("result", ""))) if status else None
                if exception is not None:
                    return exception(f"Claude Code API error {status}: {str(event.get('result', ''))[:500]}")
                break
        return super()._classify_exec_error(command, result)

    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        try:
            await super().run(instruction, environment, context)
        except asyncio.CancelledError:
            await stop_harness(environment, KILL_CLAUDE, self.environment_logs_dir.as_posix())
            raise

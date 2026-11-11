"""Harbor installed agent for nanocode (https://github.com/nanocodexyz/nanocode).

Runs nanocode as its CLI ships: `nanocode exec`, the Claude harness, the model given to
Harbor, Code Mode on (the CLI has no switch for it). The binary is the pinned official
release (scripts/fetch-nanocode.sh or the flake), uploaded into the task container.

Parity with Harbor's claude-code agent:
- the same system packages are ensured in the container (curl, bash, nodejs, npm,
  procps), so neither arm starts from a different image state;
- the instruction is passed through an environment variable that is unset before the
  harness starts, as Harbor does for Claude Code;
- errors are classified from nanocode's own `nanocode: ...` diagnostic lines only,
  never from model text or tool output (Harbor does the same for Claude Code with its
  stream-json error events);
- on timeout the harness process is killed, as agents/claude_code_agent.py does.

Authentication uses the same Claude subscription token as the claude-code agent
(CLAUDE_CODE_OAUTH_TOKEN, from `claude setup-token`). On Linux nanocode reads a Claude
Code login from $CLAUDE_SECURESTORAGE_CONFIG_DIR/.credentials.json; the token is
written there, in a root-only directory (mode 700; all task images run as root). The far-future expiry keeps nanocode from trying to refresh it.

Usage is read from nanocode's local OpenTelemetry traces by scripts/usage.py.
"""

import asyncio
import json
import os
import re
import shlex
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import (
    AgentAuthenticationError,
    BaseInstalledAgent,
    ErrorPattern,
    NetworkConnectionError,
    NonZeroAgentExitCodeError,
    with_prompt_template,
)
from harbor.agents.options import InstalledAgentOptions
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from agents.claude_code_agent import api_error, stop_harness
from scripts.usage import nanocode_usage

REMOTE_BIN = "/installed-agent/nanocode"
REMOTE_AUTH_DIR = "/installed-agent/claude-auth"
TOKEN_EXPIRES_AT_MS = 4102444800000  # 2100-01-01
# Same packages Harbor's claude-code agent ensures before installing Claude Code.
SYSTEM_DEPENDENCIES = ("curl", "bash", "nodejs", "npm", "procps")
KILL_NANOCODE = f"pkill -KILL -f '^{REMOTE_BIN} ' 2>/dev/null; true"
DIAGNOSTIC = re.compile(r"^nanocode: .*$", re.MULTILINE)
HTTP_STATUS = re.compile(r"Messages HTTP (\d{3})")


class NanocodeOptions(InstalledAgentOptions):
    # nanocode's -t/--thinking levels for Claude models
    reasoning_effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None


class Nanocode(BaseInstalledAgent):
    """nanocode `exec`, Claude harness."""

    options_model = NanocodeOptions
    options: NanocodeOptions
    capabilities = AgentCapabilities(reasoning_effort=True)
    # nanocode reports Messages API failures as "Messages HTTP <status>: <body>",
    # "Messages transport: ..." and "Claude authentication unavailable: ...".
    ERROR_PATTERNS = [
        *BaseInstalledAgent.ERROR_PATTERNS,
        # HTTP statuses go through api_error() first (_classify_exec_error).
        ErrorPattern(r"Claude authentication unavailable", AgentAuthenticationError),
        ErrorPattern(r"Messages transport:", NetworkConnectionError),
    ]

    @property
    def _reasoning_effort(self) -> str | None:
        return self.options.reasoning_effort if self.options is not None else None

    @staticmethod
    def name() -> str:
        return "nanocode"

    def get_version_command(self) -> str | None:
        return f"{REMOTE_BIN} --version"

    def parse_version(self, stdout: str) -> str:
        return stdout.strip().removeprefix("nanocode").strip()

    @property
    def _home(self) -> str:
        return (self.environment_logs_dir / "nanocode-home").as_posix()

    async def install(self, environment: BaseEnvironment) -> None:
        local = Path(os.environ.get("NANOCODE_BINARY", "vendor/nanocode")).resolve()
        if not local.is_file():
            raise RuntimeError(f"nanocode binary not found at {local}; run scripts/fetch-nanocode.sh")
        await self.ensure_system_dependencies(environment, SYSTEM_DEPENDENCIES)
        await environment.upload_file(local, REMOTE_BIN)
        await self.exec_as_root(environment, command=f"chmod 755 {REMOTE_BIN}")

    def _classify_exec_error(self, command: str, result: Any) -> NonZeroAgentExitCodeError:
        output = f"{result.stdout or ''}\n{result.stderr or ''}"
        diagnostics = DIAGNOSTIC.findall(output)
        # nanocode prints its fatal error last; earlier diagnostic lines are not the cause.
        last = diagnostics[-1] if diagnostics else ""
        match = HTTP_STATUS.search(last)
        exception = api_error(int(match.group(1)), last) if match else None
        if exception is not None:
            return exception(f"nanocode API error: {last[:500]}")
        evidence = SimpleNamespace(
            return_code=result.return_code,
            stdout=last,
            stderr="",
        )
        return super()._classify_exec_error(command, evidence)

    @with_prompt_template
    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        try:
            await self._run(instruction, environment)
        except asyncio.CancelledError:
            await stop_harness(environment, KILL_NANOCODE, self.environment_logs_dir.as_posix())
            raise

    async def _run(self, instruction: str, environment: BaseEnvironment) -> None:
        token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
        if not token:
            raise RuntimeError("CLAUDE_CODE_OAUTH_TOKEN is not set")
        if not self.model_name:
            raise RuntimeError("nanocode needs a model (-m anthropic/<model>)")
        model = self.model_name.split("/", 1)[-1]

        owner = environment.default_user if environment.default_user is not None else "root"
        await self.exec_as_root(
            environment,
            command=(
                f"mkdir -p {REMOTE_AUTH_DIR} && chown {shlex.quote(str(owner))} {REMOTE_AUTH_DIR} "
                f"&& chmod 700 {REMOTE_AUTH_DIR}"
            ),
        )
        await self._upload_config_text(
            environment,
            content=json.dumps({"claudeAiOauth": {"accessToken": token,
                                                  "expiresAt": TOKEN_EXPIRES_AT_MS}}),
            remote_path=f"{REMOTE_AUTH_DIR}/.credentials.json",
            filename=".credentials.json",
        )

        flags = ["exec", "--home", self._home, "--no-tempo-tools", "-m", model]
        if self._reasoning_effort:
            flags += ["-t", self._reasoning_effort]
        shell_var = f"nanocode_instruction_{uuid.uuid4().hex}"
        env_var = shell_var.upper()
        log = (self.environment_logs_dir / "nanocode.txt").as_posix()
        await self.exec_as_agent(
            environment,
            command=(
                f"mkdir -p {shlex.quote(self._home)}; "
                f'{shell_var}="${env_var}"; unset {env_var}; '
                f"{REMOTE_BIN} {' '.join(shlex.quote(f) for f in flags)} "
                f'"${shell_var}" 2>&1 | tee {shlex.quote(log)}'
            ),
            env={
                env_var: instruction,
                "CLAUDE_SECURESTORAGE_CONFIG_DIR": REMOTE_AUTH_DIR,
                "CLAUDE_CONFIG_DIR": REMOTE_AUTH_DIR,
                "NANOCODE_HOME": self._home,
            },
        )

    def populate_context_post_run(self, context: AgentContext) -> None:
        usage = nanocode_usage(self.logs_dir)
        if usage is None:
            return
        context.n_input_tokens = (usage["uncached_input"] + usage["cache_read"]
                                  + usage["cache_write_5m"] + usage["cache_write_1h"])
        context.n_cache_tokens = usage["cache_read"]
        context.n_output_tokens = usage["output"]
        context.cost_usd = usage["reported_cost_usd"]

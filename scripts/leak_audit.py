"""Flag trials whose agent may have looked up the task's upstream fix.

SWE-rebench tasks are real GitHub pull requests, so the fix is public. Containers have
internet access (the dependencies need it), Claude Code's web tools are off and nanocode
has none, but either harness can still run `curl`, `git fetch` or `gh` from its shell, or
look up a newer release of the package on a registry.

What is read: every tool call each harness logged (main agent and subagents).
  - Claude Code: `tool_use` blocks in agent/sessions/projects/**/*.jsonl and
    agent/claude-code.txt. Only commands are audited (Bash `command`); file reads and
    edits are not, since source code mentions its own GitHub paths (Go imports, README
    links, package metadata). A call to WebSearch, WebFetch or any MCP tool is flagged
    as such.
  - nanocode: `tool_use` blocks in agent/nanocode-home/sessions/**/*.jsonl. Its `exec`
    input is JavaScript that may both run commands and write files, so GitHub URLs count
    only next to a network command (below).
  - Any other tool: all of its string inputs.
The task instruction is never read (some instructions link the repository).

What is flagged (PATTERNS): a git remote operation, the `gh` CLI, a network command
(curl, wget, fetch(), a package manager's install/add/get, ...) followed in the same
command by a GitHub host, and registry lookups that could reveal a newer release
(pip download, npm view, proxy.golang.org, ...). A trial with model calls but no tool
call found is flagged as unaudited.

Every flagged trial is then decided by hand from its tool calls and their outputs,
before the pair's rewards are looked at, and recorded in
studies/swe-rebench/upstream_review.json as {trial: {"access": true|false, "note": ...}}.
Only confirmed access (upstream content about the fix was obtained) affects the analysis.

  python scripts/leak_audit.py <trial dir> <owner/repo>
"""

import json
import re
import sys
from pathlib import Path

# git with any global options (-C dir, -c key=value, --git-dir=...) before the subcommand
GIT_REMOTE = (r"\bgit\b(\s+(-[cC]\s+\S+|--?[\w-]+(=\S+)?))*\s+"
              r"(fetch|pull|clone|ls-remote|remote\s+(add|set-url)|submodule\s+(update|add))\b")
GITHUB = r"(github\.com|githubusercontent\.com|api\.github\.com|codeload\.github\.com|jsdelivr\.net/gh/)"
NETWORK = (r"(\bcurl\b|\bwget\b|\bfetch\s*\(|\burlopen\b|\brequests\.(get|post)\b|\bhttpx\.|\baxios\b|"
           r"\bhttps?\.(get|request)\b|" + GIT_REMOTE + r"|"
           r"\bgo\s+(get|install|mod\s+download)\b|\bpip3?\s+(install|download)\b|\buv\s+(pip|add)\b|"
           r"\b(npm|pnpm|yarn|bun)\s+(i|install|add|view|info|show|pack)\b|\bnpx\b|"
           r"\bcargo\s+(add|install|search)\b|\bmvn\b|\bgradlew?\b)")
PATTERNS = [
    ("git remote op", re.compile(GIT_REMOTE)),
    ("git remote op (argv)", re.compile(r"""["']git["']\s*,\s*\[\s*["'](fetch|pull|clone|ls-remote|remote)""")),
    ("gh CLI", re.compile(r"""(^|[\s;&|(`'"/])gh\s+(pr|issue|api|repo|search|release|browse)\b""")),
    ("gh CLI (argv)", re.compile(r"""["']gh["']\s*,\s*\[""")),
    ("network command to GitHub", re.compile(NETWORK + r"[^;&|\n]{0,300}?" + GITHUB, re.I)),
    ("registry lookup", re.compile(r"(\bpip3?\s+download\b|\bpip3?\s+index\s+versions\b|"
                                   r"\b(npm|pnpm|yarn)\s+(view|info|show|pack)\b|\bcargo\s+search\b|"
                                   r"\bmvn\b[^;&|\n]*dependency:(get|copy)|unpkg\.com|jsdelivr\.net/npm|"
                                   r"files\.pythonhosted\.org|static\.crates\.io|crates\.io/crates/|docs\.rs/|ghcr\.io/|"
                                   r"\bgo\s+list\s+-m\b[^;&|\n]*-versions|proxy\.golang\.org|deps\.dev|"
                                   r"sourcegraph\.com|pypi\.org/(pypi|simple|project)|registry\.npmjs\.org|"
                                   r"crates\.io/api|search\.maven\.org|repo1\.maven\.org)", re.I)),
]
# Claude Code tools whose input is not a command (reads, edits, searches, planning).
CC_NON_COMMAND = {"Read", "Edit", "MultiEdit", "Write", "NotebookEdit", "Glob", "Grep", "LS",
                  "TodoWrite", "Task", "Agent", "BashOutput", "KillShell", "KillBash", "TaskOutput",
                  "TaskStop", "ExitPlanMode", "EnterPlanMode", "ToolSearch", "AskUserQuestion", "Skill"}
NANOCODE_NON_COMMAND = {"wait", "wait_agent", "submit_result", "spawn_agent"}


# A pull request, issue, commit, release or archive URL of the task's repository is
# flagged in any command, with or without a network command next to it.
def upstream_url_pattern(repo: str) -> re.Pattern:
    r = re.escape(repo)
    return re.compile(rf"(api\.github\.com/repos/{r}\b|raw\.githubusercontent\.com/{r}/|codeload\.github\.com/{r}/|"
                      rf"github\.com/{r}/(pull|pulls|issues|commit|commits|compare|releases|archive|raw|blob|tree)\b)", re.I)


def package_pattern(repo: str, packages: list[str] = ()) -> re.Pattern:
    """An install or update command naming one of the task's own packages (from its
    manifests, studies/swe-rebench/image_checks.json, plus the repository name), which
    could pull a release that already contains the fix."""
    names = {p.lower() for p in packages if p} | {repo.split("/")[-1].lower()}
    alts = "|".join(sorted(re.sub(r"\\?[-_]", "[-_]?", re.escape(n)) for n in names))
    return re.compile(r"(\bpip3?\s+install|\buv\s+(pip\s+install|add|tool\s+(install|run)|run\s+--with)|\buvx|\bpipx\s+(install|run)|"
                      r"\b(npm|pnpm|yarn|bun)\s+(i|install|add|up|update|upgrade|dlx|exec)|\bnpx|\bbunx|"
                      r"\bcargo\s+(add|install|update|info)|\bgo\s+(get|install|run))\b[^;&|\n]{0,200}?[\s/@'\"=](" + alts + r")(?![\w-])",
                      re.I)


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _collect(value, out: dict) -> None:
    """Collect tool_use blocks (name, input) anywhere in a decoded JSON value, by id.
    String values holding JSON (nanocode's store keeps messages as "=<json>") are decoded."""
    if isinstance(value, dict):
        if value.get("type") in ("tool_use", "server_tool_use") and "input" in value:
            key = value.get("id") or json.dumps(value["input"], sort_keys=True)
            out[key] = (str(value.get("name", "")), value["input"])
        for v in value.values():
            _collect(v, out)
    elif isinstance(value, list):
        for v in value:
            _collect(v, out)
    elif isinstance(value, str) and "tool_use" in value:
        text = value[1:] if value.startswith("=") else value
        try:
            _collect(json.loads(text), out)
        except json.JSONDecodeError:
            pass


def tool_calls(trial_dir: Path) -> tuple[dict, list[str]]:
    agent = trial_dir / "agent"
    files = [agent / "claude-code.txt", *sorted((agent / "sessions").glob("projects/**/*.jsonl")),
             *sorted((agent / "nanocode-home" / "sessions").glob("**/*.jsonl"))]
    # Compressed nanocode sessions only appear in releases after the pinned one.
    unreadable = [str(p.relative_to(trial_dir)) for p in (agent / "nanocode-home").glob("sessions/**/*.zst")]
    calls: dict = {}
    for path in files:
        if not path.is_file():
            continue
        for line in path.read_text(errors="replace").splitlines():
            try:
                _collect(json.loads(line), calls)
            except json.JSONDecodeError:
                continue
    return calls, unreadable


def command_text(name: str, tool_input) -> str | None:
    """The part of a tool call that can run commands, or None if it cannot."""
    if name in CC_NON_COMMAND or name in NANOCODE_NON_COMMAND:
        return None
    if name == "Bash" and isinstance(tool_input, dict):
        text = str(tool_input.get("command", ""))
    elif name == "exec" and isinstance(tool_input, dict):
        text = str(tool_input.get("code", ""))
    else:
        text = "\n".join(_strings(tool_input))
    # JS/shell string escapes (`\n`, `\t`) inside nanocode's code separate commands too.
    return re.sub(r"\\[ntr]", "\n", text)


NETWORK_TO_GITHUB = PATTERNS[4][1]


def WRITTEN_UPSTREAM(repo: str) -> re.Pattern:  # noqa: N802
    """In a written file: the repository's API, raw-content or archive URL (source code
    links to github.com/<repo> pages, but has little reason to call these)."""
    r = re.escape(repo)
    return re.compile(rf"(api\.github\.com/repos/{r}\b|raw\.githubusercontent\.com/{r}/|codeload\.github\.com/{r}/)", re.I)


def audit(trial_dir: Path, repo: str, packages: list[str] = ()) -> dict:
    calls, unreadable = tool_calls(trial_dir)
    hits = []
    patterns = [*PATTERNS, ("upstream URL", upstream_url_pattern(repo)),
                ("install of the task's own package", package_pattern(repo, packages))]
    for name, tool_input in calls.values():
        if name in ("WebSearch", "WebFetch", "web_search", "web_fetch") or name.startswith("mcp__"):
            hits.append(f"{name}: {json.dumps(tool_input, ensure_ascii=False)[:200]}")
            continue
        if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            # a script written to run later: network code aimed at GitHub
            text = "\n".join(_strings(tool_input))
            m = NETWORK_TO_GITHUB.search(text) or WRITTEN_UPSTREAM(repo).search(text)
            if m:
                start = max(0, m.start() - 60)
                hits.append(f"network code to GitHub in a written file [{name}]: "
                            f"…{text[start:m.end() + 60]}…".replace("\n", "⏎"))
            continue
        text = command_text(name, tool_input)
        if text is None:
            continue
        for label, pattern in patterns:
            m = pattern.search(text)
            if m:
                start = max(0, m.start() - 60)
                hits.append(f"{label} [{name}]: …{text[start:m.end() + 60]}…".replace("\n", "⏎"))
    return {"repo": repo, "tool_calls": len(calls), "hits": hits, "unreadable": unreadable}


def review_list(job_dirs: list[Path], catalog: dict, checks: dict) -> list[dict]:
    """Flagged trials with every hit and nothing else (no rewards), for the hand review."""
    out = []
    for job in job_dirs:
        for trial in sorted(p for p in job.iterdir() if (p / "agent").is_dir()):
            # Harbor truncates trial directory names, so take the task from the config.
            task = json.loads((trial / "config.json").read_text())["task"]["name"].split("/")[-1]
            if task not in catalog:
                raise SystemExit(f"{trial}: task {task!r} is not in the study's catalog")
            a = audit(trial, catalog[task]["repo"], checks.get(task, {}).get("packages", []))
            if a["hits"] or a["unreadable"] or a["tool_calls"] == 0:
                out.append({"job": job.name, "trial": trial.name, **a})
    return out


if __name__ == "__main__":
    # python scripts/leak_audit.py <trial dir> <owner/repo>
    # BENCH_STUDY=swe-rebench python scripts/leak_audit.py --jobs jobs/swr-*   (review list)
    if sys.argv[1] == "--jobs":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from study import current
        study = current()
        catalog = json.loads((study.config_dir / "catalog.json").read_text())
        checks_file = study.config_dir / "image_checks.json"
        checks = json.loads(checks_file.read_text()) if checks_file.is_file() else {}
        jobs = [Path(p) for p in sys.argv[2:] if Path(p).is_dir() and "-oracle" not in p and "-smoke" not in p]
        print(json.dumps(review_list(jobs, catalog, checks), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(audit(Path(sys.argv[1]), sys.argv[2]), indent=2, ensure_ascii=False))

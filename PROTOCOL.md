# Protocol (fixed before any model run)

## Question

On the same Claude model and effort, how do Claude Code and nanocode compare on
Terminal-Bench 2.1 tasks, in success and in cost, tokens and time?

nanocode (https://github.com/nanocodexyz/nanocode) reuses Claude Code's system prompt
and tool descriptions (pinned from Claude Code 2.1.304), but its CLI gives Claude only
two tools, `exec` and `wait`, and Claude calls every other tool from JavaScript
("Code Mode"). It reads AGENTS.md, not CLAUDE.md, and adds no git status or memory
context. Both of these are part of what is compared.

## Arms

| | Claude Code | nanocode |
|---|---|---|
| Version | 2.1.322, installed per trial by Harbor's `claude-code` agent | official release binary, build of 2026-11-06 (commit d7a4990), sha256-pinned |
| Harbor agent | `agents/claude_code_agent.py`: Harbor's agent unchanged, plus stop-on-timeout | `agents/nanocode_agent.py` |
| Invocation | `claude --verbose --output-format=stream-json --effort medium --permission-mode=bypassPermissions --print` | `nanocode exec --no-tempo-tools -m claude-opus-5-5 -t medium` |
| Model / effort | `claude-opus-5-5` / medium | `claude-opus-5-5` / medium |
| Auth | Claude subscription token (`claude setup-token`) | the same token |
| Tools | as shipped (incl. subagents, WebSearch/WebFetch) | as shipped (`exec`/`wait`; subagents; no web tools) |
| Prompt cache | 1-hour TTL under OAuth (verified on a captured request) | 1-hour TTL |

Harbor's Claude Code agent sets `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` and
`IS_SANDBOX=1`, as in the official leaderboard runs. On a captured request the flag
leaves the system prompt and tools unchanged and only drops one deferred tool
(`DesignSync`) from the list Claude Code advertises.

`--no-tempo-tools` leaves out nanocode's paid Tempo tools (gateway key-value store,
buckets, compute, Mercator) and the local proxy through which shell commands would
reach Tempo services; all need a Tempo wallet that is not set up. nanocode still
contacts `gateway.tempo-dev.workers.dev` and `api.inference.boundless.network` at startup
(observed), apparently to list the models its `spawn_agent` can target; this is part
of nanocode as shipped and does not enter the model's context.

Both agents ensure the same system packages in the container (curl, bash, nodejs, npm,
procps; Harbor's list for Claude Code). When Harbor times an agent out, each agent kills
its own harness process (and only that) before the verifier runs, so neither keeps
calling the model or editing files during grading.

## Tasks

Terminal-Bench 2.1 (`terminal-bench/terminal-bench-2-1`), each task pinned to the
digest used by the official leaderboard runs (`configs/task_digests.json`). Selection is
fixed by `scripts/select_tasks.py` from the public Harbor Hub results of the official
leaderboard runs of Claude Code with Opus 4.8, Fable 5 and Sonnet 5 (5 trials per task):

- **primary (20):** the tasks with the highest mean outcome variance p(1-p) across those
  runs, ties broken alphabetically (9 tasks tie at the cut, 6 enter). Tasks every run
  solves or every run fails cannot show a harness difference.
- **sanity (4):** tasks every Opus 4.8 and Fable 5 trial solved, drawn with seed
  20261111, to catch an arm failing work Claude Code reliably completes.

Agent timeouts are the tasks' own: 900 s for 13 of the 24 tasks, 1800 s for 7, 2400 s
for 1, 3600 s for 3. The verifier has its own timeout.

## Environment

- Host: x86_64 Linux with KVM. Everything runs inside one microsandbox microVM
  (`scripts/vm.sh`, docker:dind pinned by digest, 12 vCPU, 12 GB, 80 GB disk) that sees
  only this repository. Each trial is a fresh container from the task's image, with the
  task's own CPU, memory, storage and timeouts.
- Internet access is on in the containers, as in the official leaderboard runs (tasks
  and verifiers install packages).
- Both arms are in the same Harbor job (`configs/job-*.json`), scheduled task by task,
  Claude Code first then nanocode, 2 trials at a time. A task's two arms start together
  and run under the same API conditions; once durations diverge they no longer overlap
  exactly. The two tasks with 8 GB memory limits (gpt2-codegolf, mteb-leaderboard) run
  in their own phase, one trial at a time, so the VM never holds two of them.
- Harbor 0.25.0 (uv.lock).

## Phases and budget

Budget: $100 API-equivalent in total across phases, enforced by
`scripts/budget_guard.py`: it prices every trial (running ones included, from their
logs so far) and stops Harbor $6 below the cap.

1. **calibration:** the first 4 primary tasks (timeouts 2400, 3600, 1800 and 900 s), 1
   attempt per arm, run with a $25 cap. Check that both arms run with the real token,
   that usage is captured, the measured cost per trial, and that Claude Code's cost
   summed from per-message events matches its final `result` event (the events are the
   only source for timed-out Claude Code trials). If the ratio is outside 0.95-1.05,
   timed-out Claude Code costs are reported as lower bounds. If the projected remaining
   phases exceed the remaining budget, stop and re-plan before running them. If the
   configuration changes after calibration, calibration trials are discarded.
2. **main:** the other primary and sanity tasks except the two 8 GB tasks, 1 attempt per
   arm, 2 trials at a time.
3. **main-big:** gpt2-codegolf and mteb-leaderboard, 1 attempt per arm, 1 at a time.
4. **rerun** (only if needed): pairs lost to API or infrastructure errors, re-run once.
   Harbor's own retries are off, because Harbor deletes a retried trial's directory and
   with it the trial's record and spend.

## Measures

Per trial: verifier reward, exception, agent wall time, and from the agent's raw logs
(`scripts/usage.py`) uncached input, cache reads, cache writes (5 min / 1 h), output
tokens, Messages API responses ("model calls": the responses each harness logs, subagents
included; Claude Code's Haiku side calls log no response and are not counted, nanocode's
prompt-cache keep-alive requests are), API retries inside a run (best effort in both arms: nanocode records them only on calls
that eventually succeed, Claude Code only if its stream reports them), and API-equivalent cost at Claude API list prices with the same table for both
arms (web searches at $10 per 1,000). Each harness's own cost figure is kept for
cross-checking only.

## Analysis (scripts/analyze.py)

- Pairing by task. Agent outcomes count, scored by the verifier's reward: a clean
  finish, a timeout, a harness crash, an exhausted context or output budget, a refusal.
- One rule for both arms. Excluded: an API status of 401, 403, 429 or 5xx reported by
  the harness (Claude Code's `api_error_status`, nanocode's last `Messages HTTP <status>`
  line), network, environment and verifier errors, and VM-level OOM kills
  (`jobs/*.vm-oom.log`), which are excluded by hand by listing the trial in
  `configs/excluded_trials.json` with the reason. A trial whose verifier produced no
  reward is excluded. Counted: any other 4xx the harness's
  own request caused (e.g. prompt too long), and a container killed at its own task
  memory limit, since a harness's memory footprint is part of what is compared.
- If either arm's trial is excluded, the whole pair is dropped and the task re-run
  (both arms) in a `rerun` job; each task uses its latest complete pair, and earlier
  attempts are listed as superseded, never averaged in. `tb21-archived-*` jobs (discarded
  runs, e.g. calibration after a configuration change) are not analysed but their
  spend counts against the budget. Trials with API retries inside
  the run, fallback pricing, usage reconstructed from events, or less than 95% of output
  tokens on claude-opus-5-5 are listed.
- Pass rate: difference with a paired bootstrap 95% interval; exact McNemar test on
  discordant tasks.
- Cost, tokens, model calls, time: per-task ratio nanocode / Claude Code, geometric mean
  with a paired bootstrap 95% interval; exact Wilcoxon signed-rank test on the log ratios.
- Reported for all tasks, primary tasks, sanity tasks, and pairs where both arms
  finished without timeout or crash (time and cost are censored on timed-out trials).
  Seven metrics over four subsets, without multiplicity correction: p-values are
  descriptive.

## What this can and cannot show

With 24 paired tasks and one attempt each, only large pass-rate gaps (roughly 25 points
or more) would be detectable; smaller ones are within noise. Efficiency differences of
about 30% or more should be clear. Tasks run up to an hour, but long-horizon behaviour
(context compaction, very long sessions) is barely exercised. Selection uses Claude Code
results only, which could favour tasks where Claude Code is unstable; the sanity tasks
check the opposite case.

## Amendment 1 (2026-11-11, before any counted trial)

The first calibration run, on an AMD Ryzen 7 2700X host with 15 GB of RAM, was stopped
after one finished trial (nanocode, compile-compcert, reward 1.0) to move to a larger
host, and is discarded. Its spend (about $0.30 recorded, at most about $0.60 more in a
Claude Code trial killed before its logs were copied out) is taken off the cap: the
remaining phases run with a $98 total cap.

All phases now run on a Google Cloud n2-custom-12-98304 VM (12 vCPU, 96 GB, nested
virtualization, europe-west1-b), inside the same microsandbox VM image with 11 vCPU and
88 GB. With that memory the 8 GB tasks no longer need to run alone. Concurrency:
calibration 4, main 6, main-big 4. Everything else is unchanged. The budget guard also
prices running trials from inside their containers (see the budget-guard fix commit), since Harbor copies
agent logs out only when a trial ends.

## Amendment 2 (2026-11-11, after calibration, before the main phases)

Calibration showed that Claude Code's stream-json assistant events carry each message's
usage from its start, without its output and thinking tokens: summed, they came to about
65% of the final `result` cost. Claude Code's session transcripts hold the final usage
and matched `result.modelUsage` exactly on all 4 calibration trials. Timed-out Claude Code
trials (no `result` event) and the budget guard's view of running trials now use the
transcripts. This changes no trial and no finished trial's measured usage, so calibration
trials are kept.

The VM-level OOM log now keeps only kernel OOM kills outside a container memory limit.
Calibration's one OOM line was a container-limit kill (nanocode, compile-compcert, a
`coqc` process; the trial still passed), which counts as an agent outcome.

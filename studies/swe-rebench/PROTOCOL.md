# Study 2 protocol: SWE-rebench (fixed before any model run)

Study 1 ([PROTOCOL.md](../../PROTOCOL.md)) compared the two harnesses on Terminal-Bench
2.1. This study asks the same question on real repository work: fixing a reported issue
in an existing codebase, across five languages. Everything not stated here is as in
study 1.

## Question

On the same Claude model and effort, how do Claude Code and nanocode compare on
SWE-rebench issue-resolution tasks, in success and in cost, tokens and time?

## Arms

As in study 1: Claude Code 2.1.322 and the nanocode release of 2026-11-06 (commit
d7a4990), both on `claude-opus-5-5` at medium effort with the same Claude subscription
token, the same Harbor agents (`agents/`) and the same system packages.

One change: Claude Code's WebSearch and WebFetch tools are turned off (Harbor 0.25.0's
`disable_web_search` option appends `WebSearch,WebFetch` to `--disallowedTools`). Each task is a merged
GitHub pull request, so the fix is public; nanocode has no web tools. Both harnesses can
still run shell commands with internet access, which the upstream-access audit covers
(below).

## Tasks

[SWE-rebench](https://swe-rebench.com), July 2026 leaderboard snapshot, as packaged for
Harbor (`ibragim-badertdinov/swe-rebench-07-2026`, 111 tasks: Go 21, Java 21, Python 20,
Rust 25, TypeScript 24). Each task is an issue from a GitHub repository, the repository
at the commit before the fix, and the pull request's tests (tests that must start
passing, and tests that must keep passing). The agent sees the issue text only; the
tests are added after it finishes.

Selection (`scripts/select_swe_rebench.py`, from `studies/swe-rebench/catalog.json`):
6 tasks per language, 30 in all, drawn with seed 20261111. Each language's tasks are
shuffled and taken in order, skipping a task whose repository is already selected, so
the 30 tasks come from 30 repositories. No public per-task results exist for this
window, so tasks are not filtered on difficulty.

Before any model run, **oracle** jobs apply each selected task's reference fix and run
its tests (no model calls), twice, to catch flaky tests. A task whose reference fix
is graded and fails either run is listed in `studies/swe-rebench/oracle_failures.json` and replaced by
the next task of the same language in the seeded order; replacements also go through
two oracle runs. An oracle trial lost to an infrastructure error (no grade) is re-run,
not counted as a failure; only tasks with two passes get a digest, so no other task can
enter a model run. If a language runs out of tasks from distinct repositories (Java has
8 repositories), stop and re-plan. Each task is pinned to the digest the oracle ran
(`studies/swe-rebench/task_digests.json`; both written by `scripts/oracle_results.py`).

Three instructions link their own repository (`mui__base-ui-4903`, `vuejs__core-14877`,
`mvanhorn__cli-printing-press-2086`), as the original issues did.

Every task gives the agent 1 CPU, 4 GB of memory and 3000 s, and the verifier 3000 s
(the dataset's settings).

**Contamination.** The issues were opened between 2026-05-15 and 2026-06-15, before
Claude Opus 5.5's training cutoff (June 2026), so the model may have seen some fixes.
This applies equally to both arms; it can make tasks easier but does not favour either
harness.

## Upstream-access audit

`scripts/leak_audit.py` reads every tool call each harness logged (main agent and
subagents), never the task text. Commands are audited: Claude Code's Bash commands,
nanocode's `exec` code, and any other tool's inputs. File reads and edits are not, since
source code mentions its own GitHub paths, except that a file written with network code
aimed at GitHub (a script to run later) is flagged. A call to WebSearch, WebFetch or an
MCP tool is flagged as such. In commands, flagged:
- a pull request, issue, commit, compare, release or archive URL of the task's
  repository, or its API or raw-content URL, however it is used;
- a git remote operation (`fetch`, `pull`, `clone`, `ls-remote`, `remote add|set-url`,
  `submodule update|add`, with any global options), the `gh`
  CLI, or a network command (curl, wget, `fetch()`, a package manager's install, ...)
  followed in the same command by a GitHub host;
- a registry lookup that could show a newer release (`pip download`, `npm view`,
  `cargo search`, `go list -m -versions`, proxy.golang.org, deps.dev, Sourcegraph, ...);
- an install or update command naming one of the task's own packages (read from the
  repository's manifests, `image_checks.json`, plus the repository name), which could
  pull a release that already contains the fix;
- a trial with model calls but no tool calls found in its logs, or with session logs
  in a format the audit cannot read (unaudited).

Each flagged trial is decided by hand from its tool calls and their outputs, listed
without rewards by `scripts/leak_audit.py --jobs`, before the pair's rewards are looked at, and recorded with a note in
`studies/swe-rebench/upstream_review.json`. **Confirmed access** means content about the
fix was obtained (the pull request, its issue thread, its commits, or a release that
contains it). The analysis refuses to run, and writes nothing, while a flagged trial is unreviewed.

Limits: a regex audit misses deliberate indirection (a URL assembled from variables or
encoded), GitHub mirrors and search engines reached by plain URLs, and anything done
through a tool output it cannot see. These are expected to be rare for an agent working
on a task; flagged-call counts per arm show whether either harness tends to look.

**Images** (checked before any model run, `studies/swe-rebench/image_checks.json`): all
30 are Debian 12 (24) or Ubuntu 24.04 (6) with apt and git (curl in 29; both agents
install it where missing), like study 1's. Both harnesses installed in all 30 (smoke). In all
30 the repository's HEAD is the base commit, with no later commits, refs, reflog,
remotes or dangling objects, so the fix is not in the image's git data.

**Repository agent configuration.** 22 of the 30 repositories ship files that coding
agents load: `CLAUDE.md` or `.claude/` (read by Claude Code), `AGENTS.md` (read by
nanocode). Both 11, Claude Code's only 6, `AGENTS.md` only 5, none 8. A developer using
either harness in these repositories would get the same, so this is part of what is
compared; results are also broken down by these four groups (descriptive).

## Environment

As in study 1 (amendment 1): a Google Cloud n2-custom-12-98304 VM, inside the
microsandbox VM (`scripts/vm.sh`, 11 vCPU, 88 GB, 160 GB disk), Harbor 0.25.0, internet
on in the containers. Both arms are in the same Harbor job, 8 trials at a time (each
task container is limited to 1 CPU; the rest is left to Docker, Harbor and the guard). A
task's two arms start together. Pulled task images are kept between jobs.

## Phases and budget

Study 2 has its own budget, separate from study 1's: **$60** API-equivalent across its
jobs (`swr-*`), enforced by `scripts/budget_guard.py`, which stops Harbor $8 below the
cap (the cap and margin are set in `scripts/study.py`).

0. **oracle** (twice) and **smoke**: reference fixes graded, then both harnesses'
   install steps run in every task image (Harbor's `install_only`). No model calls.
1. **calibration:** the first 5 tasks, one per language, 1 attempt per arm; the guard
   stops it at $15 (calibration cap $23 minus the $8 margin). Check that both arms run in these images, that usage is captured, that the
   audit finds each arm's tool calls, and the cost per trial. **Stop rule:** if the mean
   cost per calibration trial × 54 (the main phase's 50 trials plus two rerun pairs) exceeds the remaining budget ($60 minus calibration
   spend, minus the $8 margin), stop and re-plan before the main phase. If the
   configuration changes after calibration, calibration trials are discarded.
2. **main:** the other 25 tasks, 1 attempt per arm.
3. **rerun** (only if needed): pairs lost to API or infrastructure errors, re-run once,
   both arms together.

## Measures and analysis

As in study 1 (`scripts/usage.py`, `scripts/analyze.py`): reward, exception, agent wall
time, tokens, model calls and API-equivalent cost per trial; the same exclusion rule for
both arms (infrastructure and API errors excluded, agent outcomes counted); pairs
dropped if either trial is excluded; pass-rate difference with a paired bootstrap 95%
interval and exact McNemar test; per-task ratios nanocode / Claude Code with geometric
means, bootstrap intervals and Wilcoxon tests. The reward is 1 only if every target
test passes and no previously passing test fails.

Subsets reported:
- **primary:** paired tasks where neither arm had confirmed upstream access;
- **sensitivity:** all paired tasks, with a trial that had confirmed access scored 0;
- **sensitivity:** all paired tasks as graded;
- pairs without confirmed access where both arms finished without timeout or crash.

Flagged and confirmed counts are reported per arm (a harness that looks upstream more
often is itself a finding), with each flagged call's text. Timeouts and container memory
kills are listed per arm. p-values are descriptive.

## What this can and cannot show

With 30 paired tasks and one attempt each, only large pass-rate gaps (roughly 25 points
or more) would be detectable. Together with study 1 it shows whether the two harnesses
stay in the same range on a different kind of work: longer exploration of an unfamiliar
codebase, edits across files, and running a project's own test suite.

## Amendment 1 (2026-11-11, after calibration, before the main phase)

Calibration cost $8.78 for 10 trials ($0.88 per trial; Claude Code $4.49, nanocode $4.29).
By the stop rule, $0.88 × 54 = $47 exceeded the remaining budget ($60 − $8.78 − $8 = $43),
so the main phase was not started. Study 2's cap is raised to **$75** (agreed with the
repository owner), keeping all 30 tasks; nothing else changes. Calibration trials are
kept: the configuration is unchanged. Calibration's two flagged trials (both arms, ruff)
were reviewed before rewards were read: an issue URL inside a code comment written with
`sed`/`printf`, and the repository's `uvx prek` hook run matched by a path; no access.

# harness-bench

Does the agent harness change how well the same model codes?

This repo runs two harnesses on the **same model**, the **same tasks** and the **same
machine**, and compares them task by task. Only the harness differs.

## Study 1: Claude Code vs nanocode

|  | Claude Code | nanocode |
|---|---|---|
| What it is | Anthropic's coding agent | an open-source Rust agent SDK that reuses Claude Code's prompts |
| Version | 2.1.322 | release of 2026-11-06 (commit d7a4990) |
| Model | Claude Opus 5.5, medium effort | Claude Opus 5.5, medium effort |

- **Tasks:** 24 tasks from [Terminal-Bench 2.1](https://tbench.ai), chosen from public
  leaderboard results as the ones where Claude's outcome varies most (plus 4 easy checks).
- **Measured:** tasks solved, cost, tokens, model calls and time, for each task.
- **Isolation:** everything runs inside a [microsandbox](https://github.com/superradcompany/microsandbox)
  VM; each trial gets a fresh container. No personal config, MCP servers or skills.
- **Rules:** fixed in advance in [PROTOCOL.md](PROTOCOL.md).

### Results (2026-11-11)

23 tasks compared, one attempt per harness ([full results](results/summary.md),
[every trial](results/trials.csv)).

|  | Claude Code | nanocode |
|---|---|---|
| Tasks solved | 19 / 23 | 18 / 23 |
| Total cost (API-equivalent) | $7.90 | $5.70 |

- **Solved:** no detectable difference. Each harness solved a few tasks the other
  didn't (Claude Code 3, nanocode 2). The difference is -4 points, 95% CI -22 to +13.
- **Cost per task:** nanocode was 26% cheaper on average (95% CI 56% cheaper to 11%
  more expensive), so not a clear difference either.
- **Time:** on the 20 tasks both finished normally, nanocode took about 22% longer
  (95% CI -5% to +52%).
- **Refusals:** Claude's safety classifier stopped both harnesses on `dna-assembly`, and
  stopped nanocode only on `feal-linear-cryptanalysis`, which Claude Code solved.
- **Excluded:** `qemu-startup`, because Debian no longer serves the packages its image
  needs to install either harness (twice, both harnesses).

With 23 tasks and one attempt each, only large differences would show. This says
nanocode is in the same range as Claude Code on these tasks, not that they are equal.

## Study 2: Claude Code vs nanocode on SWE-rebench

Same harnesses, versions and model as study 1, on real repository work: fixing a GitHub
issue in an existing codebase.

- **Tasks:** 30 from [SWE-rebench](https://swe-rebench.com) (July 2026 snapshot), 6 per
  language (Go, Java, Python, Rust, TypeScript), each from a different repository, drawn
  with a fixed seed. Each task's reference fix was checked to pass its tests twice.
- **Fixes are public:** Claude Code's web tools were off (nanocode has none), and every
  trial's commands were checked for attempts to fetch the upstream fix.
- **Rules:** fixed in advance in [studies/swe-rebench/PROTOCOL.md](studies/swe-rebench/PROTOCOL.md).

### Results (2026-11-11)

30 tasks compared, one attempt per harness ([full results](studies/swe-rebench/results/summary.md),
[every trial](studies/swe-rebench/results/trials.csv)).

|  | Claude Code | nanocode |
|---|---|---|
| Tasks solved | 19 / 30 | 20 / 30 |
| Total cost (API-equivalent) | $28.25 | $27.59 |
| Hit the 50-minute time limit | 3 | 0 |

- **Solved:** no detectable difference. Claude Code solved 2 tasks nanocode didn't,
  nanocode 3 that Claude Code didn't. The difference is +3 points, 95% CI -10 to +17.
- **Cost per task:** nanocode was 10% cheaper on average (95% CI 2% to 18% cheaper),
  mostly from reading fewer input tokens (18% fewer).
- **Time:** nanocode took 21% less time per task (95% CI 3% to 35% less).
- **Fix lookups:** 7 trials were flagged (4 Claude Code, 3 nanocode); on review none
  had fetched the fix. Two fetched TinkerPop source code that their task said to port.
- **Caveats:** the issues are from May to June 2026, before Opus 5.5's training cutoff,
  so the model may have seen some fixes (equally in both harnesses). 22 of the 30
  repositories ship agent instruction files, which Claude Code (`CLAUDE.md`) and
  nanocode (`AGENTS.md`) read differently; this is part of what was compared.

Across both studies, nanocode solved about as many tasks as Claude Code with the same
model, at similar or lower cost.

## How it works

1. [Harbor](https://github.com/harbor-framework/harbor) runs each task once with each harness.
2. Each task's grader decides pass or fail.
3. Tokens are read from each harness's own logs and priced the same way for both.
4. A budget guard stops the run at a spending cap.
5. [`scripts/analyze.py`](scripts/analyze.py) compares the two harnesses task by task.

## Run it yourself

You need an x86_64 Linux machine with KVM, [microsandbox](https://github.com/superradcompany/microsandbox),
[uv](https://docs.astral.sh/uv/) and a Claude subscription.

```sh
scripts/fetch-nanocode.sh                 # pinned nanocode binary (or: nix develop)
scripts/vm.sh up                          # VM with Docker and Harbor
claude setup-token                        # then save the token:
(umask 077; cat > ~/.bench-token)         # paste it, Enter, Ctrl-D
scripts/run.sh calibration                # 4 tasks first, to check cost
scripts/run.sh main                       # the rest
scripts/run.sh main-big                   # the two 8 GB tasks
uv run python scripts/analyze.py          # writes results/summary.md
scripts/vm.sh down
```

Study 2: set `BENCH_STUDY=swe-rebench` and run the phases `oracle`, `smoke`,
`calibration` and `main` (see its protocol).

Costs are API-equivalent dollars from token counts at Claude API list prices. On a
subscription nothing is billed per token.

## Files

| Path | What |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | the full design, fixed before any run |
| [`agents/`](agents/) | Harbor agents for both harnesses |
| [`configs/`](configs/) | study 1's tasks and their pinned versions |
| [`studies/swe-rebench/`](studies/swe-rebench/) | study 2: protocol, tasks, image checks, results |
| [`scripts/`](scripts/) | task selection, VM, runs, budget guard, cost, leak audit, analysis |
| [`data/hub/`](data/hub/) | public leaderboard results used to pick tasks |

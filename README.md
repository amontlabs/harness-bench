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

Costs are API-equivalent dollars from token counts at Claude API list prices. On a
subscription nothing is billed per token.

## Files

| Path | What |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | the full design, fixed before any run |
| [`agents/`](agents/) | Harbor agents for both harnesses |
| [`configs/`](configs/) | selected tasks and their pinned versions |
| [`scripts/`](scripts/) | task selection, VM, runs, budget guard, cost, analysis |
| [`data/hub/`](data/hub/) | public leaderboard results used to pick tasks |

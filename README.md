# Claude Code vs nanocode, same Claude model

A small, paired comparison of [Claude Code](https://claude.com/claude-code) and
[nanocode](https://github.com/nanocodexyz/nanocode) on
[Terminal-Bench 2.1](https://tbench.ai) tasks, both running Claude Opus 5.5 at medium
effort. Design, task selection and analysis are fixed in [PROTOCOL.md](PROTOCOL.md)
before any run. Results go in `results/`.

## Layout

| Path | What |
|---|---|
| `PROTOCOL.md` | the pre-registered design |
| `agents/claude_code_agent.py` | Harbor's Claude Code agent, plus stop-on-timeout |
| `agents/nanocode_agent.py` | Harbor agent for nanocode |
| `scripts/select_tasks.py` | task selection from public Harbor Hub results (`data/hub/`) |
| `configs/tasks.json` | the selected tasks |
| `configs/task_digests.json` | task digests of the official leaderboard runs |
| `scripts/make_job.py` | Harbor job config per phase |
| `scripts/vm.sh` | the microsandbox VM that runs everything |
| `scripts/run.sh` | runs a phase in the VM, with the budget guard |
| `scripts/usage.py` | tokens and API-equivalent cost from each agent's raw logs |
| `scripts/budget_guard.py` | stops a job at a spend cap |
| `scripts/analyze.py` | paired statistics, `results/summary.md` |

## Reproduce

Needs an x86_64 Linux host with KVM, [microsandbox](https://github.com/superradcompany/microsandbox)
(`msb`, tested with 0.7.14), [uv](https://docs.astral.sh/uv/) and a Claude subscription.

```sh
nix develop                 # or: scripts/fetch-nanocode.sh   (pinned nanocode binary in vendor/)
python scripts/select_tasks.py            # optional: regenerates configs/tasks.json
scripts/vm.sh up                          # microVM with Docker and Harbor
claude setup-token                        # on any machine with a browser; then on the host:
(umask 077; cat > ~/.bench-token)         # paste the token, Enter, Ctrl-D
BENCH_CAP=25 scripts/run.sh calibration   # first 4 tasks
scripts/run.sh main                       # the rest; total cap $100 across phases
scripts/run.sh main-big                   # the two 8 GB tasks, one at a time
uv run python scripts/analyze.py jobs/tb21-*/
scripts/vm.sh down
```

Costs are API-equivalent dollars computed from token counts at Claude API list prices;
on a subscription they are not billed.

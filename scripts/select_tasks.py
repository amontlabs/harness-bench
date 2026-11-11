"""Pick the Terminal-Bench 2.1 tasks this comparison runs, from public Harbor Hub results.

Input: data/hub/tasks-<model>.json, the per-task breakdowns of the official TB 2.1
leaderboard runs of Claude Code with Opus 4.8 (high), Fable 5 (xhigh) and Sonnet 5
(high), 5 trials per task, fetched with `harbor hub job tasks <job> --json`.
(tasks-opus47.json is kept for reference; it has complete data for 20 tasks only and is
not used.)

Output: configs/tasks.json with
  - "primary": the 20 tasks whose outcomes vary most across those runs. A task every
    run solves (or every run fails) carries no information about a harness difference.
  - "sanity": 4 tasks every Opus 4.8 and Fable 5 trial solved, drawn with a fixed seed,
    to catch a harness failing work Claude Code reliably completes.

The selection uses Claude Code results only; nanocode has no public results. Tasks are
ranked by mean Bernoulli variance p(1-p) over the Opus 4.8, Fable 5 and Sonnet 5 runs,
ties broken alphabetically (9 tasks tie at the 20th place's variance, 0.133; 6 enter).
"""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ("opus48", "fable5", "sonnet5")
N_PRIMARY = 20
N_SANITY = 4
SEED = 20261111


def load() -> dict[str, dict[str, float]]:
    rewards: dict[str, dict[str, float]] = {}
    for run in RUNS:
        items = json.loads((ROOT / "data/hub" / f"tasks-{run}.json").read_text())["items"]
        for item in items:
            if item.get("agent_name") != "claude-code" or item.get("n_trials") != 5:
                continue
            reward = item["evals"]["reward"]["metrics"][0]["reward"]
            rewards.setdefault(item["task_name"].split("/")[-1], {})[run] = reward
    return {task: runs for task, runs in rewards.items() if len(runs) == len(RUNS)}


def main() -> None:
    rewards = load()
    variance = {t: sum(p * (1 - p) for p in r.values()) / len(r) for t, r in rewards.items()}
    informative = sorted((t for t, v in variance.items() if v > 0), key=lambda t: (-variance[t], t))
    primary = informative[:N_PRIMARY]
    always = sorted(t for t, r in rewards.items() if r["opus48"] == 1 and r["fable5"] == 1)
    sanity = sorted(random.Random(SEED).sample(always, N_SANITY))
    out = {
        "dataset": "terminal-bench/terminal-bench-2-1",
        "seed": SEED,
        "primary": primary,
        "sanity": sanity,
        "reference_rewards": {t: rewards[t] for t in primary + sanity},
    }
    (ROOT / "configs/tasks.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"{len(rewards)} tasks with complete data; {len(informative)} informative")
    print("primary:", primary)
    print("sanity:", sanity)


if __name__ == "__main__":
    main()

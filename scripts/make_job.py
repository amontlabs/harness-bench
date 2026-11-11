"""Write the Harbor job config for one phase from configs/tasks.json.

Both arms run in the same job, so Harbor schedules their trials together (task by task,
arm by arm) and every trial of a task uses the same task digest, image and limits.
Tasks are pinned to the digests of the official TB 2.1 leaderboard runs
(configs/task_digests.json, read from those runs' Harbor Hub trials).

  calibration: the first 4 primary tasks, one attempt per arm
  main:        the remaining primary and sanity tasks except the two with 8 GB memory
               limits, 2 trials at a time
  main-big:    gpt2-codegolf and mteb-leaderboard (8 GB limits), 1 trial at a time, so
               the VM (12 GB) never holds two of them

No Harbor-level retries: Harbor deletes a retried trial's directory, which would erase
its spend and its record. Trials that end on an API or infrastructure error are
re-run by hand in a later job (see PROTOCOL.md).
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "anthropic/claude-opus-5-5"
EFFORT = "medium"
CLAUDE_CODE_VERSION = "2.1.322"
N_CALIBRATION = 4
BIG_MEMORY = ["gpt2-codegolf", "mteb-leaderboard"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["calibration", "main", "main-big", "rerun"])
    parser.add_argument("--tasks", nargs="*", default=[], help="task names, for rerun")
    args = parser.parse_args()

    tasks = json.loads((ROOT / "configs/tasks.json").read_text())
    digests = json.loads((ROOT / "configs/task_digests.json").read_text())
    rest = tasks["primary"][N_CALIBRATION:] + tasks["sanity"]
    names, concurrency = {
        "calibration": (tasks["primary"][:N_CALIBRATION], 2),
        "main": ([t for t in rest if t not in BIG_MEMORY], 2),
        "main-big": ([t for t in rest if t in BIG_MEMORY], 1),
        "rerun": (args.tasks, 1),
    }[args.phase]
    if not names:
        raise SystemExit("no tasks")
    missing = [n for n in names if n not in digests]
    if missing:
        raise SystemExit(f"no pinned digest for {missing}")
    org = tasks["dataset"].split("/")[0]

    job = {
        "job_name": f"tb21-{args.phase}",
        "jobs_dir": "jobs",
        "n_attempts": 1,
        "n_concurrent_trials": concurrency,
        "retry": {"max_retries": 0},
        "agents": [
            {
                "import_path": "agents.claude_code_agent:ClaudeCodeAgent",
                "model_name": MODEL,
                "kwargs": {"reasoning_effort": EFFORT, "version": CLAUDE_CODE_VERSION},
            },
            {
                "import_path": "agents.nanocode_agent:Nanocode",
                "model_name": MODEL,
                "kwargs": {"reasoning_effort": EFFORT},
            },
        ],
        "tasks": [
            {"name": f"{org}/{n}", "ref": digests[n], "source": tasks["dataset"]} for n in names
        ],
    }
    out = ROOT / "configs" / f"job-{args.phase}.json"
    out.write_text(json.dumps(job, indent=2) + "\n")
    print(f"{out} ({len(names)} tasks x 2 arms)")


if __name__ == "__main__":
    main()

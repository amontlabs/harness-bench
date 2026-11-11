"""Write the Harbor job config for one phase of the current study (scripts/study.py).

Both arms run in the same job, so Harbor schedules their trials together (task by task,
arm by arm) and every trial of a task uses the same task digest, image and limits.
Tasks are pinned to the digests in the study's task_digests.json (study 1: those of the
official TB 2.1 leaderboard runs; study 2: those recorded by the study's oracle job).

  calibration: the first n_calibration primary tasks (scripts/study.py), one attempt per arm
  main:        the remaining primary and sanity tasks except the two with 8 GB memory
               limits, 2 trials at a time
  main-big:    the study's big-memory tasks (study 1: gpt2-codegolf and mteb-leaderboard,
               8 GB limits), 1 trial at a time by default
  oracle:      every task with Harbor's oracle agent (the reference solution, no model,
               no cost), pinned to known digests (new tasks: latest); its lock.json gives the digests to pin

No Harbor-level retries: Harbor deletes a retried trial's directory, which would erase
its spend and its record. Trials that end on an API or infrastructure error are
re-run by hand in a later job (see PROTOCOL.md).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from study import current  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODEL = "anthropic/claude-opus-5-5"
EFFORT = "medium"
CLAUDE_CODE_VERSION = "2.1.322"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["calibration", "main", "main-big", "rerun", "oracle", "smoke"])
    parser.add_argument("--tasks", nargs="*", default=[], help="task names, for rerun")
    parser.add_argument("--concurrency", type=int, help="override the phase's default")
    args = parser.parse_args()

    study = current()
    tasks = json.loads(study.tasks_file.read_text())
    every = tasks["primary"] + tasks.get("sanity", [])
    rest = tasks["primary"][study.n_calibration:] + tasks.get("sanity", [])
    names, concurrency = {
        "calibration": (tasks["primary"][:study.n_calibration], 2),
        "main": ([t for t in rest if t not in study.big_memory], 2),
        "main-big": ([t for t in rest if t in study.big_memory], 1),
        "rerun": (args.tasks, 2),  # a pair's two arms start together
        # oracle: the reference solutions, graded (no model). smoke: both harnesses'
        # install steps only, no model call and no grading (Harbor's install_only).
        "oracle": (args.tasks or every, 4),
        "smoke": (args.tasks or every, 4),
    }[args.phase]
    if not names:
        raise SystemExit("no tasks")
    if study.concurrency and args.phase in ("calibration", "main"):
        concurrency = study.concurrency
    concurrency = args.concurrency or concurrency
    org = tasks["dataset"].split("/")[0]
    if args.phase == "oracle":  # pinned where known; new tasks get pinned from this run
        pinned = json.loads(study.digests_file.read_text()) if study.digests_file.is_file() else {}
        refs = {n: pinned.get(n, "latest") for n in names}
    else:
        digests = json.loads(study.digests_file.read_text())
        missing = [n for n in names if n not in digests]
        if missing:
            raise SystemExit(f"no pinned digest for {missing}")
        refs = digests

    job = {
        "job_name": f"{study.prefix}-{args.phase}",
        "jobs_dir": "jobs",
        "n_attempts": 1,
        "n_concurrent_trials": concurrency,
        "retry": {"max_retries": 0},
        "agents": [
            {
                "import_path": "agents.claude_code_agent:ClaudeCodeAgent",
                "model_name": MODEL,
                "kwargs": {"reasoning_effort": EFFORT, "version": CLAUDE_CODE_VERSION,
                           **study.claude_code_kwargs},
            },
            {
                "import_path": "agents.nanocode_agent:Nanocode",
                "model_name": MODEL,
                "kwargs": {"reasoning_effort": EFFORT},
            },
        ],
        "tasks": [
            {"name": f"{org}/{n}", "ref": refs[n], "source": tasks["dataset"]} for n in names
        ],
    }
    if args.phase == "oracle":
        job["agents"] = [{"name": "oracle"}]
    if args.phase == "smoke":
        job["install_only"] = True
    out = ROOT / "configs" / f"job-{study.prefix}-{args.phase}.json"
    out.write_text(json.dumps(job, indent=2) + "\n")
    print(f"{out} ({len(names)} tasks x {len(job['agents'])} agents)")


if __name__ == "__main__":
    main()

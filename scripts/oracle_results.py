"""Read the study's oracle jobs (jobs/<prefix>-oracle*) and write
  - <config_dir>/oracle_failures.json: tasks whose reference solution failed in any oracle
    run (reward below 1 or an exception), with the reason; select_swe_rebench.py skips them;
  - <config_dir>/task_digests.json: the digest each task ran at, from the jobs' lock.json.
A task run at two different digests is an error. Prints which selected tasks still need
an oracle run or two passing runs.

  BENCH_STUDY=swe-rebench python scripts/oracle_results.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from study import current  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS_NEEDED = 2  # PROTOCOL: a task's reference solution must pass twice


def main() -> None:
    study = current()
    jobs = sorted(p for p in (ROOT / "jobs").glob(f"{study.prefix}-oracle*") if p.is_dir())
    digests: dict[str, str] = {}
    passes: dict[str, int] = defaultdict(int)
    failures: dict[str, str] = {}
    errors: list[str] = []
    for job in jobs:
        lock = json.loads((job / "lock.json").read_text())
        for trial in lock["trials"]:
            name, digest = trial["task"]["name"].split("/")[-1], trial["task"]["digest"]
            if digests.setdefault(name, digest) != digest:
                raise SystemExit(f"{name} ran at two digests: {digests[name]} and {digest}")
        for result in sorted(job.glob("*/result.json")):
            d = json.loads(result.read_text())
            name = d["task_name"].split("/")[-1]
            reward = ((d.get("verifier_result") or {}).get("rewards") or {}).get("reward")
            exc = (d.get("exception_info") or {}).get("exception_type")
            if reward == 1.0 and exc is None:
                passes[name] += 1
            elif reward is not None:  # the reference fix was graded and failed
                failures[name] = f"{job.name}: reward {reward}, exception {exc}"
            else:  # infrastructure (pull, build, verifier crash): not a verdict on the task
                errors.append(f"{name} in {job.name}: {exc}")

    out = study.config_dir
    (out / "oracle_failures.json").write_text(json.dumps(dict(sorted(failures.items())), indent=2) + "\n")
    # Only tasks whose reference fix passed every run, at least RUNS_NEEDED times, are
    # pinned, so make_job.py refuses any other task for model runs.
    ready = {n: d for n, d in digests.items() if n not in failures and passes[n] >= RUNS_NEEDED}
    (out / "task_digests.json").write_text(json.dumps(dict(sorted(ready.items())), indent=2) + "\n")
    selected = json.loads(study.tasks_file.read_text())["primary"]
    print(f"{len(jobs)} oracle jobs; {len(failures)} failed tasks: {sorted(failures)}")
    if errors:
        print(f"infrastructure errors (re-run these): {errors}")
    short = [t for t in selected if t not in failures and passes[t] < RUNS_NEEDED]
    print(f"selected tasks without {RUNS_NEEDED} passing oracle runs: {short or 'none'}")
    bad = [t for t in selected if t in failures]
    if bad:
        print(f"selected tasks that failed (re-run select_swe_rebench.py): {bad}")
    if short or bad:
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Pick the SWE-rebench tasks study 2 runs.

Input: a local copy of the Harbor dataset ibragim-badertdinov/swe-rebench-07-2026
(111 tasks; `harbor datasets download` or any Harbor job's task cache), read only for
each task's tests/config.json. The fields used are copied to
studies/swe-rebench/catalog.json, so the selection can be re-checked without the download:

  python scripts/select_swe_rebench.py --dataset <dir>   # rebuild catalog, then select
  python scripts/select_swe_rebench.py                   # select from the catalog

Output: studies/swe-rebench/tasks.json with "primary": 6 tasks per language (Go, Java,
Python, Rust, TypeScript; 30 in all), drawn with a fixed seed: each language's tasks
are shuffled and taken in order, skipping a task whose repository is already in the
list, so no repository appears twice. No public
per-task results exist for this window, so tasks are not filtered on difficulty. The
list is ordered round-robin over languages, so the first 5 (the calibration phase) are
one per language.

Tasks listed in studies/swe-rebench/oracle_failures.json (their reference solution did
not pass their own tests in the oracle job) are skipped, so the next task of the same
language in the seeded order takes their place.
"""

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "studies" / "swe-rebench"
DATASET = "ibragim-badertdinov/swe-rebench-07-2026"
PER_LANGUAGE = 6
SEED = 20261111
FIELDS = ("repo", "pull_number", "pr_url", "issue_number", "created_at", "base_commit",
          "language", "image_name")


def build_catalog(dataset: Path) -> dict:
    catalog = {}
    for task in sorted(dataset.iterdir()):
        config = task / "tests" / "config.json"
        if config.is_file():
            data = json.loads(config.read_text())
            catalog[task.name] = {k: data.get(k) for k in FIELDS}
            created = catalog[task.name]["created_at"]  # epoch ms or an ISO string
            if isinstance(created, (int, float)) or str(created).isdigit():
                created = datetime.fromtimestamp(int(created) / 1000, timezone.utc).isoformat()
            catalog[task.name]["created_at"] = str(created)[:10]
    if len(catalog) != 111:
        raise SystemExit(f"expected 111 tasks, found {len(catalog)}")
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, help="local copy of the Harbor dataset")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    catalog_file = OUT / "catalog.json"
    if args.dataset:
        catalog_file.write_text(json.dumps(build_catalog(args.dataset), indent=1) + "\n")
    catalog = json.loads(catalog_file.read_text())
    failures_file = OUT / "oracle_failures.json"
    failures = json.loads(failures_file.read_text()) if failures_file.is_file() else {}

    rng = random.Random(SEED)
    by_language = {}
    for language in sorted({t["language"] for t in catalog.values()}):
        names = sorted(n for n, t in catalog.items() if t["language"] == language)
        rng.shuffle(names)
        picked, repos = [], set()
        for name in names:
            if name not in failures and catalog[name]["repo"] not in repos and len(picked) < PER_LANGUAGE:
                picked.append(name)
                repos.add(catalog[name]["repo"])
        by_language[language] = picked
    primary = [by_language[lang][i] for i in range(PER_LANGUAGE) for lang in sorted(by_language)]

    (OUT / "tasks.json").write_text(json.dumps({
        "dataset": DATASET,
        "seed": SEED,
        "oracle_failures": sorted(failures),
        "primary": primary,
        "language": {n: catalog[n]["language"] for n in primary},
    }, indent=2) + "\n")
    print(f"{len(primary)} tasks: " + ", ".join(f"{k} {len(v)}" for k, v in by_language.items()))


if __name__ == "__main__":
    main()

"""The studies in this repo. Scripts pick one with BENCH_STUDY (default: tb21).

  tb21          study 1: Terminal-Bench 2.1 (PROTOCOL.md)
  swe-rebench   study 2: SWE-rebench, July 2026 window (studies/swe-rebench/PROTOCOL.md)

Each study has its own task list, pinned task digests, job-name prefix (so budgets
and analyses never mix) and results directory.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Study:
    name: str
    prefix: str  # job names: <prefix>-calibration, <prefix>-main, ...
    dataset: str
    config_dir: Path
    results_dir: Path
    n_calibration: int = 4
    cap: float = 100.0  # USD API-equivalent across the study's jobs (scripts/run.sh, BENCH_CAP overrides)
    margin: float = 6.0  # the budget guard stops Harbor this far below the cap
    calibration_cap: float | None = None  # cap for the calibration phase (default: cap)
    concurrency: int | None = None  # trials at a time for calibration/main (default: make_job's)
    keep_images: bool = False  # keep pulled task images between jobs (fewer Docker Hub pulls)
    big_memory: tuple[str, ...] = ()
    # Extra kwargs for Harbor's claude-code agent, on top of model, effort and version.
    claude_code_kwargs: dict = field(default_factory=dict)

    @property
    def tasks_file(self) -> Path:
        return self.config_dir / "tasks.json"

    @property
    def digests_file(self) -> Path:
        return self.config_dir / "task_digests.json"


STUDIES = {
    "tb21": Study(
        name="tb21",
        prefix="tb21",
        dataset="terminal-bench/terminal-bench-2-1",
        config_dir=ROOT / "configs",
        results_dir=ROOT / "results",
        big_memory=("gpt2-codegolf", "mteb-leaderboard"),
    ),
    "swe-rebench": Study(
        name="swe-rebench",
        prefix="swr",
        dataset="ibragim-badertdinov/swe-rebench-07-2026",
        config_dir=ROOT / "studies" / "swe-rebench",
        results_dir=ROOT / "studies" / "swe-rebench" / "results",
        n_calibration=5,  # one task per language
        cap=75.0,  # amendment 1: raised from 60 after calibration
        margin=8.0,
        calibration_cap=23.0,  # the guard stops at $15 (cap - margin)
        concurrency=8,
        keep_images=True,
        # The fixes are public on GitHub; nanocode has no web tools, so Claude Code's are
        # turned off too (Harbor's disable_web_search, as in Scale's SWE-bench Pro protocol).
        claude_code_kwargs={"disable_web_search": True},
    ),
}


# A study's jobs are found by `<prefix>-*`, so no prefix may extend another with a hyphen.
assert not any(a.prefix.startswith(b.prefix + "-") for a in STUDIES.values() for b in STUDIES.values())


def current() -> Study:
    name = os.environ.get("BENCH_STUDY", "tb21")
    if name not in STUDIES:
        raise SystemExit(f"unknown BENCH_STUDY {name!r}; one of {sorted(STUDIES)}")
    return STUDIES[name]


if __name__ == "__main__":  # `python scripts/study.py prefix` prints a field for shell scripts
    print(getattr(current(), sys.argv[1]))

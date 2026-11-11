"""Stop a running Harbor job before total spend reaches the cap.

Every `--interval` seconds it prices, with scripts/usage.py, every finished trial of
every job under jobs/ whose name starts with `tb21-`, and every trial still running,
from the logs inside its container (Harbor copies them out only at the end): Claude
Code's stream-json so far, nanocode's spans so far. When
spent + margin >= cap it sends SIGTERM to Harbor (which cancels its trials), and
SIGKILL if Harbor is still alive two minutes later. Any error in the guard itself also
stops Harbor: it fails closed.

  python scripts/budget_guard.py --pid <harbor pid> --cap 100 --margin 6
"""

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from usage import trial_usage  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def live_costs() -> dict[str, float]:
    """Spend of trials still running. Harbor copies agent logs out of a container only
    when the trial ends, so read them from the running containers (named
    `<trial name, lowercased>__env-main-1`) into a temp dir and price them."""
    out = subprocess.run(["docker", "ps", "--format", "{{.Names}}"],
                         capture_output=True, text=True, check=True).stdout.split()
    costs = {}
    for name in out:
        if not name.endswith("__env-main-1"):
            continue
        trial = name.removesuffix("__env-main-1")
        with tempfile.TemporaryDirectory() as tmp:
            agent = Path(tmp) / "agent"
            otel = agent / "nanocode-home" / "log" / "otel" / "live"
            otel.mkdir(parents=True)
            for remote, local in (("/logs/agent/claude-code.txt", agent / "claude-code.txt"),
                                  ("/logs/agent/nanocode-home/log/otel/*/traces.jsonl", otel / "traces.jsonl")):
                text = subprocess.run(["docker", "exec", name, "sh", "-c", f"cat {remote} 2>/dev/null"],
                                      capture_output=True, text=True).stdout
                if text:
                    local.write_text(text)
            usage = trial_usage(Path(tmp))
            if usage is not None:
                costs[trial] = usage["cost_usd"]
    return costs


def spent(jobs_dir: Path) -> tuple[float, int]:
    costs: dict[str, float] = {}
    for job in sorted(jobs_dir.glob("tb21-*")):
        if not job.is_dir():
            continue
        for trial in job.iterdir():
            if trial.is_dir() and (trial / "agent").is_dir():
                usage = trial_usage(trial)
                if usage is not None:
                    costs[f"{job.name}/{trial.name.lower()}"] = usage["cost_usd"]
    finished = {key.split("/", 1)[1] for key in costs}
    for trial, cost in live_costs().items():
        if trial not in finished:
            costs[f"live/{trial}"] = cost
    return sum(costs.values()), len(costs)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def stop(pid: int, reason: str) -> None:
    print(f"stopping Harbor: {reason}", flush=True)
    os.kill(pid, signal.SIGTERM)
    for _ in range(120):
        if not alive(pid):
            return
        time.sleep(1)
    print("Harbor still alive after SIGTERM: SIGKILL", flush=True)
    os.kill(pid, signal.SIGKILL)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--cap", type=float, required=True, help="total USD across all tb21-* jobs")
    parser.add_argument("--margin", type=float, default=6.0,
                        help="stop this much below the cap, for trials in flight")
    parser.add_argument("--jobs-dir", type=Path, default=ROOT / "jobs")
    parser.add_argument("--interval", type=float, default=20.0)
    args = parser.parse_args()

    while alive(args.pid):
        try:
            total, n = spent(args.jobs_dir)
        except Exception:
            traceback.print_exc()
            stop(args.pid, "the budget guard failed to price trials")
            return
        print(f"{time.strftime('%H:%M:%S')} ${total:.2f} over {n} trials "
              f"(cap ${args.cap:.2f}, margin ${args.margin:.2f})", flush=True)
        if total + args.margin >= args.cap:
            stop(args.pid, f"spent ${total:.2f} + margin ${args.margin:.2f} >= cap ${args.cap:.2f}")
            return
        time.sleep(args.interval)
    total, n = spent(args.jobs_dir)
    print(f"Harbor exited: ${total:.2f} over {n} trials in total", flush=True)


if __name__ == "__main__":
    main()

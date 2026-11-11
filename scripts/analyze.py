"""Paired comparison of the two arms across one or more Harbor job directories.

  python scripts/analyze.py            # every jobs/tb21-* except tb21-archived-*

For every trial: arm (Harbor agent name), task, reward, exception, agent wall time and
usage priced by scripts/usage.py. Outputs results/trials.csv and results/summary.md.

Pairing: a pair is the two arms' trials of a task in the same job, both counted (see
below). If either arm's trial is excluded, the whole pair is dropped; a later job that
re-ran the task (`rerun`) supplies it instead. Each task uses its latest complete pair;
earlier attempts are listed as superseded, never averaged in. tb21-archived-* jobs
(discarded runs) are not analysed; the budget guard still counts their spend.

Statistics (stdlib only):
  - pass rate (verifier reward, whatever the agent's exit status): exact two-sided
    McNemar test on discordant tasks, and a paired bootstrap 95% interval on the
    difference;
  - cost, tokens, model calls, time: per-task ratio nanocode / Claude Code, geometric
    mean with a paired bootstrap 95% interval, and an exact two-sided Wilcoxon
    signed-rank test on the log ratios (the same quantity).
One rule decides for both arms. Excluded: an API status of 401, 403, 429 or >= 500
reported by the harness (Claude Code's `api_error_status`, nanocode's `Messages HTTP`),
and any exception outside the agent outcomes below (network, environment, verifier,
cancellation). Counted: a clean finish, a timeout, a harness crash, an exhausted
context or output budget, a refusal, and any other 4xx the harness's own request
caused. Seven metrics over four task subsets are reported without multiplicity
correction: read p-values as descriptive.
"""

import csv
import json
import math
import random
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from usage import trial_usage  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ARMS = ("claude-code", "nanocode")
AGENT_OUTCOMES = {
    None, "AgentTimeoutError", "NonZeroAgentExitCodeError", "ContextWindowExceededError",
    "OutputTokenExceededError", "AgentSafetyRefusalError",
}


def infra_status(status: int) -> bool:
    return status in (401, 403, 429) or status >= 500


EXCLUDED_BY_HAND = (json.loads((ROOT / "configs/excluded_trials.json").read_text())
                    if (ROOT / "configs/excluded_trials.json").is_file() else {})


def counted(r: dict) -> bool:
    """The single exclusion rule, applied identically to both arms."""
    if r["trial"] in EXCLUDED_BY_HAND or r["reward"] is None:  # hand exclusion; verifier failed
        return False
    try:
        status = int(r.get("api_error_status") or 0)
    except (TypeError, ValueError):
        status = 0
    if status and infra_status(status):
        return False
    if r["exception"] == "UnknownApiError":  # Claude Code: counted only for a harness-caused 4xx
        return bool(status)
    return r["exception"] in AGENT_OUTCOMES


def job_order(name: str) -> tuple:
    phases = {"tb21-calibration": 0, "tb21-main": 1, "tb21-main-big": 2}
    natural = [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)]
    return (phases.get(name, 3), natural)
B = 20000
RNG = random.Random(20261111)


def seconds(span: dict | None) -> float | None:
    if not span or not span.get("started_at") or not span.get("finished_at"):
        return None
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return (parse(span["finished_at"]) - parse(span["started_at"])).total_seconds()


def oom_trials(job_dirs: list[Path]) -> set[str]:
    """Names of containers Docker reported killed for memory (cgroup limit). Harbor's
    compose project, and so the container name, starts with the trial name."""
    names = set()
    for job in job_dirs:
        log = job.parent / f"{job.name}.oom.log"
        if log.is_file():
            names |= {line.split()[-1] for line in log.read_text().splitlines() if line.split()}
    return names


def telemetry_lost(trial_dir: Path) -> bool:
    """nanocode reports dropped or unwritten local trace spans on stderr."""
    log = trial_dir / "agent" / "nanocode.txt"
    if not log.is_file():
        return False
    text = log.read_text(errors="replace")
    return "local OTLP spans" in text or "failed to write local OTLP telemetry" in text


def compose_name(name: str) -> str:
    """Harbor's docker compose project name for a trial (dots and the like become '-')."""
    return re.sub(r"[^a-z0-9_-]", "-", name.lower())


def load(job_dirs: list[Path]) -> list[dict]:
    rows = []
    ooms = oom_trials(job_dirs)
    for job in job_dirs:
        for result in sorted(job.glob("*/result.json")):
            d = json.loads(result.read_text())
            if "agent_info" not in d:
                continue
            exc = (d.get("exception_info") or {}).get("exception_type")
            rewards = (d.get("verifier_result") or {}).get("rewards") or {}
            usage = trial_usage(result.parent) or {}
            rows.append({
                "job": job.name, "trial": d["trial_name"], "arm": d["agent_info"]["name"],
                "container_oom": any(compose_name(d["trial_name"]) in compose_name(o) for o in ooms),
                "agent_version": d["agent_info"].get("version"),
                "task": d["task_name"].split("/")[-1], "task_ref": d["task_id"]["ref"],
                "reward": rewards.get("reward"), "exception": exc,
                "agent_sec": seconds(d.get("agent_execution")),
                "cost_usd": usage.get("cost_usd"), "input_total": usage.get("input_total"),
                "uncached_input": usage.get("uncached_input"), "cache_read": usage.get("cache_read"),
                "cache_write": (usage.get("cache_write_5m", 0) or 0) + (usage.get("cache_write_1h", 0) or 0)
                if usage else None,
                "output": usage.get("output"), "model_calls": usage.get("model_calls"),
                "reported_cost_usd": usage.get("reported_cost_usd"),
                "api_retries": usage.get("api_retries"),
                "api_error_status": usage.get("api_error_status"),
                "events_cost_usd": usage.get("events_cost_usd"),
                "events_over_result": (usage["events_cost_usd"] / usage["cost_usd"])
                if usage.get("events_cost_usd") and usage.get("cost_usd") else None,
                "main_model_output_share": (sum(u["output"] for m, u in usage["models"].items()
                                                if m.startswith("claude-opus-5-5")) / usage["output"])
                if usage.get("output") else None,
                "telemetry_lost": telemetry_lost(result.parent),
                "usage_source": usage.get("source"),
                "priced_by_fallback": usage.get("priced_by_fallback"),
                "models": json.dumps(sorted(usage.get("models", {}))),
            })
    return rows


def mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def wilcoxon_p(diffs: list[float]) -> float:
    """Exact two-sided Wilcoxon signed-rank p (zeros dropped, mid-ranks for ties)."""
    d = [x for x in diffs if x != 0]
    n = len(d)
    if n == 0:
        return 1.0
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    scaled = [round(r * 2) for r in ranks]  # integers, so mid-ranks stay exact
    w_plus = sum(s for s, x in zip(scaled, d) if x > 0)
    dist = {0: 1}
    for s in scaled:
        nxt = defaultdict(int)
        for total, count in dist.items():
            nxt[total] += count
            nxt[total + s] += count
        dist = nxt
    total = sum(scaled)
    lower = min(w_plus, total - w_plus)
    p = sum(c for t, c in dist.items() if t <= lower) / 2**n
    return min(1.0, 2 * p)


def boot(values: list[float], stat) -> tuple[float, float]:
    samples = sorted(stat([RNG.choice(values) for _ in values]) for _ in range(B))
    return samples[int(0.025 * B)], samples[int(0.975 * B) - 1]


def median(xs: list[float]) -> float:
    xs = sorted(xs)
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


EFFICIENCY = [("cost_usd", "API-equivalent cost ($)"), ("input_total", "input tokens (incl. cache)"),
              ("uncached_input", "uncached input tokens"), ("cache_write", "cache-write tokens"),
              ("output", "output tokens"), ("model_calls", "model calls"),
              ("agent_sec", "agent wall time (s)")]


def section(title: str, tasks: list[str], mean) -> list[str]:
    lines = [f"## {title} ({len(tasks)})", ""]
    cc = [mean(t, "claude-code", "reward") for t in tasks]
    nc = [mean(t, "nanocode", "reward") for t in tasks]
    diffs = [n - c for n, c in zip(nc, cc)]
    lo, hi = boot(diffs, lambda xs: sum(xs) / len(xs))
    b = sum(1 for c, n in zip(cc, nc) if c == 1 and n == 0)
    c_ = sum(1 for c, n in zip(cc, nc) if c == 0 and n == 1)
    lines += ["| | Claude Code | nanocode | difference (nanocode - CC), 95% CI |",
              "|---|---|---|---|",
              f"| mean reward | {sum(cc)/len(cc):.3f} | {sum(nc)/len(nc):.3f} | "
              f"{sum(diffs)/len(diffs):+.3f} [{lo:+.3f}, {hi:+.3f}] |", "",
              f"Discordant tasks: Claude Code only {b}, nanocode only {c_}; "
              f"exact McNemar p = {mcnemar_p(b, c_):.3f}.", "",
              "| metric | CC median | nanocode median | ratio nanocode/CC (geo. mean, 95% CI) | Wilcoxon p | n |",
              "|---|---|---|---|---|---|"]
    for key, label in EFFICIENCY:
        pairs = [(mean(t, "claude-code", key), mean(t, "nanocode", key)) for t in tasks]
        pairs = [(c, n) for c, n in pairs if c is not None and n is not None]
        if not pairs:
            continue
        ratio_pairs = [(c, n) for c, n in pairs if c > 0 and n > 0]
        if ratio_pairs:
            logs = [math.log(n / c) for c, n in ratio_pairs]
            lo, hi = boot(logs, lambda xs: sum(xs) / len(xs))
            ratio = f"{math.exp(sum(logs) / len(logs)):.2f} [{math.exp(lo):.2f}, {math.exp(hi):.2f}]"
            p = f"{wilcoxon_p(logs):.3f}"
        else:
            ratio, p = "n/a", "n/a"
        lines.append(f"| {label} | {median([c for c, _ in pairs]):,.2f} | {median([n for _, n in pairs]):,.2f} | "
                     f"{ratio} | {p} | {len(ratio_pairs)} |")
    return lines + [""]


def main() -> None:
    jobs = [Path(p) for p in sys.argv[1:]] or [p for p in (ROOT / "jobs").glob("tb21-*") if p.is_dir()]
    jobs = sorted((j for j in jobs if not j.name.startswith("tb21-archived-")), key=lambda j: job_order(j.name))
    rows = load(jobs)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    with open(out / "trials.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["trial"])
        writer.writeheader()
        writer.writerows(rows)

    excluded = [r for r in rows if not counted(r)]
    by_job_task = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_job_task[(r["job"], r["task"])][r["arm"]].append(r)
    per: dict = {}
    superseded, dropped = [], []
    for (job, task), arms in sorted(by_job_task.items(), key=lambda kv: job_order(kv[0][0])):
        complete = all(len(arms.get(a, [])) == 1 and counted(arms[a][0]) for a in ARMS)
        if complete:
            if task in per:
                superseded.append((task, per[task]["claude-code"][0]["job"]))
            per[task] = {a: arms[a] for a in ARMS}
        else:
            dropped.append((task, job))
    dropped = [(t, j) for t, j in dropped if t not in per or job_order(j) > job_order(per[t]["claude-code"][0]["job"])]
    paired = sorted(per)

    def mean(task: str, arm: str, key: str) -> float | None:
        vals = [r[key] if key != "reward" else (r["reward"] or 0.0) for r in per[task][arm]]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    lines = ["# Results", "", f"Jobs: {', '.join(j.name for j in jobs)}", "",
             f"Paired tasks: {len(paired)}. Excluded trials (infrastructure errors): {len(excluded)}.", ""]
    for r in excluded:
        reason = EXCLUDED_BY_HAND.get(r["trial"]) or ("no verifier reward" if r["reward"] is None else "")
        lines.append(f"- excluded {r['trial']} ({r['arm']}): {r['exception']} {reason}".rstrip()
                     + (f", API status {r['api_error_status']}" if r.get("api_error_status") else ""))
    for task, job in dropped:
        lines.append(f"- pair dropped: {task} in {job} (an arm excluded or missing; needs a rerun)")
    for task, job in superseded:
        lines.append(f"- superseded: {task} in {job} (a later job re-ran it)")
    flagged = [r for r in rows if (r.get("api_retries") or 0) > 0 or r.get("priced_by_fallback")
               or r.get("usage_source") not in ("result.modelUsage", "otel spans")
               or (r.get("main_model_output_share") is not None and r["main_model_output_share"] < 0.95)
               or r.get("container_oom") or r.get("telemetry_lost")]
    for r in flagged:
        lines.append(f"- note {r['trial']} ({r['arm']}): api_retries={r['api_retries']}, "
                     f"usage from {r['usage_source']}, fallback pricing={r['priced_by_fallback']}, "
                     f"opus-5-5 output share={r['main_model_output_share']}, "
                     f"container killed at its memory limit={r['container_oom']}, "
                     f"nanocode telemetry lost (usage undercounted)={r['telemetry_lost']}")
    ratios = [r["events_over_result"] for r in rows if r.get("events_over_result")]
    if ratios:
        lines.append(f"- Claude Code cost from session transcripts / from result event, finished trials: "
                     f"median {median(ratios):.3f}, range {min(ratios):.3f}-{max(ratios):.3f} (n={len(ratios)}). "
                     "Costs of timed-out Claude Code trials come from the transcripts; far from 1 means they are biased.")
    for oom in sorted((ROOT / "jobs").glob("tb21-*vm-oom.log")) if (ROOT / "jobs").is_dir() else []:
        text = oom.read_text().strip()
        if text:
            lines.append(f"- VM-level OOM kills in {oom.name}: affected trials must be excluded by hand "
                         f"and re-run (container-limit OOMs are flagged per trial and count):"
                         f"\n```\n{text[:2000]}\n```")
    if excluded or flagged or dropped or superseded:
        lines.append("")
    lines += ["model calls = Messages API responses, subagents included, in both arms.", ""]

    selection = json.loads((ROOT / "configs/tasks.json").read_text())
    finished = [t for t in paired if all(r["exception"] is None for a in ARMS for r in per[t][a])]
    subsets = [("all paired tasks", paired),
               ("primary tasks", [t for t in paired if t in selection["primary"]]),
               ("sanity tasks", [t for t in paired if t in selection["sanity"]]),
               ("pairs where both arms finished (no timeout or crash)", finished)]
    for title, tasks in subsets:
        if tasks:
            lines += section(title, tasks, mean)

    total = {a: sum(r["cost_usd"] or 0 for r in rows if r["arm"] == a) for a in ARMS}
    lines += ["", "## Spend (API-equivalent)", "",
              *[f"- {a}: ${v:.2f} over {sum(1 for r in rows if r['arm'] == a)} trials" for a, v in total.items()],
              f"- total: ${sum(total.values()):.2f}", "",
              "## Per task", "", "| task | CC reward | nanocode reward | CC $ | nanocode $ | CC s | nanocode s |",
              "|---|---|---|---|---|---|---|"]
    for t in paired:
        f2 = lambda v: "-" if v is None else f"{v:.2f}"  # noqa: E731
        lines.append(f"| {t} | {f2(mean(t,'claude-code','reward'))} | {f2(mean(t,'nanocode','reward'))} | "
                     f"{f2(mean(t,'claude-code','cost_usd'))} | {f2(mean(t,'nanocode','cost_usd'))} | "
                     f"{f2(mean(t,'claude-code','agent_sec'))} | {f2(mean(t,'nanocode','agent_sec'))} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

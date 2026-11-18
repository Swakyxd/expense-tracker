"""Runs the experiments from the implementation plan (§10.3) on data/test_sms.csv.

    python eval/run_eval.py --exp E1,E2,E4 --batch-size 30   # fits one model's free-tier day (20 requests)
    python eval/run_eval.py --runs 3                          # the plan's full design; needs a paid key

Every LLM response is cached in eval/results/.cache (per model), so an interrupted run resumes for free.
"""
import argparse
import statistics
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from metrics import FIELDS, failures, score  # noqa: E402

from pipeline import categorize as cat, llm  # noqa: E402
from pipeline.extract import batches, extract_batch  # noqa: E402
from pipeline.preprocess import preprocess  # noqa: E402
from pipeline.schema import Sms  # noqa: E402

RESULTS = ROOT / "eval" / "results"
VERSIONS = ["v1", "v2", "v3", "v4"]


def load_gold(name: str = "test_sms.csv") -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / name, dtype={"date": str}).set_index("id")


def run_pipeline(gold, version, use_filter=False, batch_size=10):
    """Full pipeline on the test set → (predictions indexed by id, metrics)."""
    first_call = len(llm.STATS)
    kept, noise, _ = preprocess([Sms(i, text) for i, text in gold["sms"].items()], use_filter)
    rows, infos = [], []
    for batch in batches(kept, batch_size):
        batch_rows, info = extract_batch(batch, version)
        rows += batch_rows
        infos.append(info)
    cat._cache.clear()
    cat.categorize(rows)
    pred = pd.DataFrame(rows).set_index("id")
    calls = llm.STATS[first_call:]
    return pred, score(gold, pred) | {
        "valid_json_rate": sum(i["valid_json"] for i in infos) / len(infos),
        "repairs_per_batch": sum(i["repairs"] for i in infos) / len(infos),
        "api_calls": len(calls),
        "sms_sent_to_llm": len(kept),
        "transactions_wrongly_dropped": int(gold.loc[[m.id for m in noise], "is_transaction"].sum()),
        "tokens_per_sms": sum(c["prompt_tokens"] + c["output_tokens"] for c in calls) / len(gold),
        "latency_per_sms": sum(c["latency"] for c in calls) / len(gold),
    }


def run_categorizer(gold, use_rules, use_llm):
    """E4: categorizer alone, fed the gold merchant/type/mode so extraction errors don't leak in."""
    first_call = len(llm.STATS)
    txns = gold[gold["is_transaction"]].reset_index().rename(columns={"sms": "raw_sms"})
    rows = txns.astype(object).where(txns.notna(), None).to_dict("records")
    truth = [r.pop("category") for r in rows]
    cat._cache.clear()
    cat.categorize(rows, use_rules=use_rules, use_llm=use_llm)
    return None, {
        "category_accuracy": sum(r["category"] == t for r, t in zip(rows, truth)) / len(rows),
        "decided_by_rules": sum(r["category_source"] == "rule" for r in rows),
        "api_calls": len(llm.STATS) - first_call,
    }


def experiments(gold, hard, batch_size):
    return {
        "E1": {v: lambda v=v: run_pipeline(gold, v, batch_size=batch_size) for v in VERSIONS},
        # same ablation on data/test_sms_hard.csv: edge cases the core set is too easy to expose
        "E1H": {v: lambda v=v: run_pipeline(hard, v, batch_size=batch_size) for v in VERSIONS},
        "E2": {f"filter_{'on' if f else 'off'}": lambda f=f: run_pipeline(gold, "v4", use_filter=f, batch_size=batch_size)
               for f in (False, True)},
        # the plan's batch size 1 is 61 requests per run, three days of free-tier quota: use 10 / 30 / 60 instead
        "E3": {f"batch_{n}": lambda n=n: run_pipeline(gold, "v3", batch_size=n) for n in (10, 30, 60)},
        "E4": {
            "rules_only": lambda: run_categorizer(gold, True, False),
            "llm_only": lambda: run_categorizer(gold, False, True),
            "hybrid": lambda: run_categorizer(gold, True, True),
        },
    }


def ablation_chart(e1: pd.DataFrame, path: Path, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ramp = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # one hue, light → dark: v1 → v4 is an ordered scale
    ink, grid, surface = "#52514e", "#e1e0d9", "#fcfcfb"
    acc = e1.pivot(index="metric", columns="config", values="mean") * 100
    fig, ax = plt.subplots(figsize=(10, 4.5), facecolor=surface)
    ax.set_facecolor(surface)
    width = 0.19 * 6 / len(FIELDS)
    for k, version in enumerate(VERSIONS):
        xs = [x + (k - 1.5) * (width + 0.01) for x in range(len(FIELDS))]
        bars = ax.bar(xs, [acc.at[f"{f}_accuracy", version] for f in FIELDS], width, color=ramp[k], label=version)
        if version == VERSIONS[-1]:  # label only the final version; the axis carries the rest
            ax.bar_label(bars, fmt="%.0f%%", fontsize=8, color=ink, padding=2)
    ax.set_xticks(range(len(FIELDS)), [f.capitalize() for f in FIELDS])
    ax.set_ylim(0, 108)
    ax.set_yticks(range(0, 101, 20), [f"{t}%" for t in range(0, 101, 20)])
    ax.yaxis.grid(True, color=grid, linewidth=1)
    ax.set_axisbelow(True)
    ax.tick_params(colors=ink, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.set_title(title, loc="left", fontsize=11, color="#0b0b0b")
    ax.legend(ncol=4, frameon=False, loc="upper right", bbox_to_anchor=(1, 1.1), labelcolor=ink)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def failure_log(gold, preds: dict, path: Path):
    fails = {v: failures(gold, p) for v, p in preds.items()}
    first, last = VERSIONS[0], VERSIONS[-1]
    still_wrong = {f["id"] for f in fails[last]}
    lines = ["# Failure log", "",
             "Run 1 of each prompt version (pre-filter off). "
             "\"Likely cause\" is an automatic first guess; review it by hand, and check the label too.", "",
             f"## Before / after candidates (wrong in {first}, fully correct in {last})", ""]
    for f in [f for f in fails[first] if f["id"] not in still_wrong][:3]:
        lines += [f"- **SMS {f['id']}**, `{f['field']}`: {first} returned `{f['predicted']}`, expected `{f['expected']}` ({f['cause']})",
                  f"  > {f['sms']}", ""]
    for version, items in fails.items():
        lines += [f"## {version}: {len(items)} wrong predictions", "",
                  "| id | field | expected | predicted | likely cause | SMS |", "|---|---|---|---|---|---|"]
        lines += [f"| {f['id']} | {f['field']} | {f['expected']} | {f['predicted']} | {f['cause']} | {f['sms'].replace('|', '/')} |"
                  for f in items]
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--exp", default="E1,E1H,E2,E3,E4", help="comma-separated experiments (default: all)")
    parser.add_argument("--runs", type=int, default=1, help="runs per configuration (default: 1; the plan asks for 3)")
    parser.add_argument("--batch-size", type=int, default=30, help="SMS per LLM call in E1, E1H and E2 (default: 30)")
    args = parser.parse_args()

    llm.CACHE_DIR = RESULTS / ".cache"
    cat.CACHE_FILE = None
    gold, hard = load_gold(), load_gold("test_sms_hard.csv")
    rows, first_run_preds = [], {"E1": {}, "E1H": {}}
    try:
        for name in args.exp.upper().split(","):
            for config, run in experiments(gold, hard, args.batch_size)[name].items():
                per_run = []
                for r in range(1, args.runs + 1):
                    llm.SALT = f"run{r}"
                    pred, metrics = run()
                    per_run.append(metrics)
                    if name in first_run_preds and r == 1:
                        first_run_preds[name][config] = pred
                    print(f"{name} {config} run {r}: " + ", ".join(f"{k}={v:.3g}" for k, v in metrics.items()), flush=True)
                for metric in per_run[0]:
                    values = [float(m[metric]) for m in per_run]
                    rows.append({"experiment": name, "config": config, "metric": metric, "model": llm.MODEL,
                                 "mean": round(statistics.mean(values), 4), "std": round(statistics.pstdev(values), 4),
                                 "runs": " ".join(f"{v:.4g}" for v in values)})
    except RuntimeError as e:  # quota or missing key: keep the configurations that finished
        print(f"\nStopped during {name} {config}: {e}\nFinished calls are cached; re-run the same command to resume.")
    if not rows:
        sys.exit(1)

    results = pd.DataFrame(rows)
    out = RESULTS / "results.csv"
    if out.exists():  # keep experiments that were not re-run this time
        old = pd.read_csv(out)
        results = pd.concat([old[~old["experiment"].isin(results["experiment"])], results]).sort_values("experiment", kind="stable")
    results.to_csv(out, index=False)

    written = [str(out)]
    for name, suffix, data, label in (("E1", "", gold, "core set"), ("E1H", "_hard", hard, "hard set")):
        if len(first_run_preds[name]) == len(VERSIONS):  # only when the whole ablation finished
            model = results.loc[results["experiment"] == name, "model"].iloc[0]
            ablation_chart(results[results["experiment"] == name], RESULTS / f"ablation_chart{suffix}.png",
                           f"Field accuracy by prompt version, {label} ({model})")
            failure_log(data, first_run_preds[name], RESULTS / f"failure_log{suffix}.md")
            written += [f"ablation_chart{suffix}.png", f"failure_log{suffix}.md"]
    for name, table in results.groupby("experiment"):
        print(f"\n{name}\n" + table.pivot(index="metric", columns="config", values="mean")
              .loc[table["metric"].unique(), table["config"].unique()].round(3).to_string())
    print("\nWrote " + ", ".join(written))


if __name__ == "__main__":
    main()

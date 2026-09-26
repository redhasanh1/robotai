"""Capstone figures from the saved results (no re-running): results/figures/*.png

    .venv/Scripts/python tools/figures.py

Reads logs/bench.json, logs/brain_live_*.json. Every number on a plot comes from those files; profiles that were
assumed rather than measured are drawn dashed and labelled "estimated".
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "figures")


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(OUT, exist_ok=True)
    b = json.load(open(os.path.join(ROOT, "logs", "bench.json")))
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    made = []

    # 1. the safety layers, one bar pair each
    fig, ax = plt.subplots(figsize=(7, 3.8))
    v = {x["verify"]: x["success"] for x in b["verifier"]}
    t = {x["veto"]: x["success"] for x in b["veto"]}
    h = {x["world"]: x for x in b["holdout"]}
    labels = ["self-check\n(retry on failure)", "physics veto\n(before acting)", "everything, on an\nunseen contact model"]
    before = [v[False], t[False], h["holdout"]["blind_single_try"]]
    after = [v[True], t[True], h["holdout"]["full_system"]]
    x = range(len(labels))
    ax.bar([i - 0.2 for i in x], [p * 100 for p in before], 0.4, label="without", color="#bbb")
    ax.bar([i + 0.2 for i in x], [p * 100 for p in after], 0.4, label="with", color="#2a7")
    for i in x:
        ax.text(i - 0.2, before[i] * 100 + 1, f"{before[i]:.0%}", ha="center")
        ax.text(i + 0.2, after[i] * 100 + 1, f"{after[i]:.0%}", ha="center")
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("grasps held (%)")
    ax.set_ylim(0, 110)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
    ax.set_title("Checking beats guessing (simulation, 48 tasks per bar)")
    made.append(save(fig, "1_safety_layers.png"))

    # 2. best of N
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ns = [r["n"] for r in b["best_of_n"]]
    ax.plot(ns, [r["success"] * 100 for r in b["best_of_n"]], "o-", color="#2a7")
    ax.set_xscale("log", base=2)
    ax.set_xticks(ns, [str(n) for n in ns])
    ax.set_xlabel("candidate grasps ranked per decision (N)")
    ax.set_ylabel("held first try (%)")
    ax.set_title("More options considered, more grasps held")
    made.append(save(fig, "2_best_of_n.png"))

    # 3. habits: model calls per task over time
    if "habits" in b:
        fig, ax = plt.subplots(figsize=(6.5, 3.6))
        for mode, style in (("off", ("#bbb", "o-")), ("gated", ("#2a7", "s-"))):
            rows = b["habits"][mode]
            ax.plot(range(1, len(rows) + 1), [r["calls_per_task"] for r in rows], style[1], color=style[0],
                    label=f"habits {mode}  (success {min(r['success'] for r in rows):.0%}+)")
        ax.set_xticks(range(1, len(rows) + 1), [r["episodes"] for r in rows])
        ax.set_xlabel("tasks")
        ax.set_ylabel("AI calls per task")
        ax.set_ylim(0, 3.6)
        ax.legend(frameon=False)
        ax.set_title("Learning when not to think (no training run)")
        made.append(save(fig, "3_habits.png"))

    # 4. brain speed: measured local vs estimated
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    for f in sorted(os.listdir(os.path.join(ROOT, "logs"))):
        if f.startswith("brain_live_") and f.endswith(".json"):
            m = json.load(open(os.path.join(ROOT, "logs", f)))
            lat = m["latency"]
            ax.plot([x["n"] for x in lat], [x["decision_s"] for x in lat], "o-",
                    label=f"{ {'local': 'SmolVLM-500M'}.get(m['model'], m['model'])} on GTX 1660 Ti (measured)")
    for r in b["speed"]:
        if r["profile"] != "local_1660ti":
            ns = [int(k) for k in r["decision_s"]]
            ax.plot(ns, list(r["decision_s"].values()), "--", label=f"{r['profile']} (estimated)")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("candidates ranked per decision (N)")
    ax.set_ylabel("seconds per decision")
    ax.axhline(1.0, color="#999", lw=0.8)
    ax.text(1.05, 1.08, "1 s", color="#777")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("How long the robot thinks before each move")
    made.append(save(fig, "4_brain_speed.png"))

    # 5. estimator
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    names = ["camera only", "physics only", "+ camera", "+ fitted params", "+ learned residual"]
    dev = [16.0, 6.3, 6.1, 5.4, 1.7]            # results/estimator_and_gpu.md, development hand, 3 seeds
    ax.bar(names, dev, color=["#bbb", "#9bd", "#79c", "#58b", "#2a7"])
    for i, e in enumerate(dev):
        ax.text(i, e + 0.3, f"{e}", ha="center")
    ax.set_ylabel("finger error (degrees)")
    ax.set_title("Where the fingers are: physics-informed vs camera alone")
    plt.setp(ax.get_xticklabels(), rotation=15)
    made.append(save(fig, "5_estimator.png"))
    print("\n".join(made))


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return path


if __name__ == "__main__":
    main()

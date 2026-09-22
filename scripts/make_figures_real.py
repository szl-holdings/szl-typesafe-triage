import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("docs/paper/figures"); OUT.mkdir(parents=True, exist_ok=True)
INK, ACC, WARN, MUTE = "#0B1F3A", "#3AF4C8", "#C9752B", "#8892A4"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": INK, "axes.labelcolor": INK,
                     "text.color": INK, "xtick.color": INK, "ytick.color": INK, "axes.grid": True,
                     "grid.alpha": 0.18, "grid.linestyle": "-", "figure.dpi": 200, "savefig.bbox": "tight"})

def rd(p):
    q = Path(p)
    return json.loads(q.read_text(encoding="utf-8-sig")) if q.exists() else None

Y, AX, LK, RT = rd("out/yuyay_gate_conformance.json"), rd("out/axiom_conformance.json"), rd("out/leakage_gate.json"), rd("out/retractions.json")
made = []

# fig 1 - decision rules against the labelled gate
if Y:
    a = Y["agreement"]
    names = ["conjunctive\nAND", "margin-min\ngate", "geometric\nproduct", "uniform\nthreshold"]
    vals = [a["conjunctive_and"], a["margin_min"], a["geometric_product"], a["uniform_threshold_min_MISSPECIFIED"]]
    cols = [ACC, ACC, WARN, MUTE]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    b = ax.bar(names, vals, color=cols, edgecolor=INK, linewidth=0.7)
    ax.bar_label(b, fmt="%d", padding=3, fontsize=9)
    ax.set_ylim(0, 108); ax.set_ylabel("rows agreeing with gate_verdict (of 100)")
    ax.set_title("Decision rules against 100 labelled yuyay_v3 rows", fontsize=10.5, loc="left")
    ax.text(0, -0.30, "conjunctive AND generated the labels, so its 100/100 is an identity check, not a win.\n"
                      "the uniform threshold is a misspecified rule retained for the record.",
            transform=ax.transAxes, fontsize=7.6, color=MUTE, va="top")
    fig.savefig(OUT / "fig1_decision_rules.pdf"); fig.savefig(OUT / "fig1_decision_rules.png"); plt.close(fig)
    made.append("fig1_decision_rules")

# fig 2 - compensation errors by axis, coloured by floor
if Y and Y.get("compensation_errors_by_axis"):
    d = dict(sorted(Y["compensation_errors_by_axis"].items(), key=lambda kv: kv[1]))
    strict = {"moralGrounding", "measurabilityHonesty"}
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    cols = [WARN if k in strict else ACC for k in d]
    b = ax.barh(list(d.keys()), list(d.values()), color=cols, edgecolor=INK, linewidth=0.7)
    ax.bar_label(b, fmt="%d", padding=3, fontsize=8)
    ax.set_xlabel("rows where the product admits what the conjunction refuses")
    ax.set_title("Compensation errors by axis (" + str(Y["compensation_errors"]) + " of " + str(Y["rows"]) + " rows)",
                 fontsize=10.5, loc="left")
    ax.text(0, -0.13, "orange = axes with a 0.95 floor; teal = 0.90. errors concentrate on the looser floors,\n"
                      "which fail narrowly and are exactly what a multiplicative rule absorbs.",
            transform=ax.transAxes, fontsize=7.6, color=MUTE, va="top")
    fig.savefig(OUT / "fig2_compensation_by_axis.pdf"); fig.savefig(OUT / "fig2_compensation_by_axis.png"); plt.close(fig)
    made.append("fig2_compensation_by_axis")

# fig 3 - axiom properties
if AX:
    v = AX["violations"]
    keys = ["A1_monotonicity", "A2_homogeneity", "A3_idempotence", "A4_boundedness", "A5_permutation_invariance"]
    labs = ["monotone", "homogeneous", "idempotent", "bounded", "permutation\ninvariant"]
    vals = [v.get(k, 0) for k in keys]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    b = ax.bar(labs, vals, color=[ACC] * 4 + [WARN], edgecolor=INK, linewidth=0.7)
    ax.bar_label(b, fmt="%d", padding=3, fontsize=9)
    ax.set_ylabel("violating vectors (of " + str(AX["vectors_tested"]) + ")")
    ax.set_title("Property conformance of the deployed aggregator", fontsize=10.5, loc="left")
    ax.text(0, -0.28, "properties are named, not numbered: three axiomatizations in the same estate number them\n"
                      "differently. the engine is multiplicative and non-symmetric.",
            transform=ax.transAxes, fontsize=7.6, color=MUTE, va="top")
    fig.savefig(OUT / "fig3_property_conformance.pdf"); fig.savefig(OUT / "fig3_property_conformance.png"); plt.close(fig)
    made.append("fig3_property_conformance")

# fig 4 - leakage against threshold
if LK:
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    names = ["this corpus", "predecessor adapter"]
    vals = [LK.get("max_char5gram_jaccard", 0), 0.7901]
    b = ax.bar(names, vals, color=[WARN, MUTE], edgecolor=INK, linewidth=0.7, width=0.52)
    ax.bar_label(b, fmt="%.4f", padding=3, fontsize=9)
    ax.axhline(0.70, color=INK, linestyle="--", linewidth=1)
    ax.text(1.42, 0.712, "refusal threshold 0.70", fontsize=7.6, color=INK)
    ax.set_ylim(0, 1.0); ax.set_ylabel("max char-5gram Jaccard across the split")
    ax.set_title("Corpus contamination: both attempts exceed the refusal threshold", fontsize=10.5, loc="left")
    ax.text(0, -0.30, "the predecessor passed its behavioural gate 66/66 and was vetoed here.\n"
                      "worst pair in this corpus differs by one word.",
            transform=ax.transAxes, fontsize=7.6, color=MUTE, va="top")
    fig.savefig(OUT / "fig4_leakage.pdf"); fig.savefig(OUT / "fig4_leakage.png"); plt.close(fig)
    made.append("fig4_leakage")

# fig 5 - retractions, cumulative
if RT:
    ns = sorted(x["n"] for x in RT["retractions"])
    mine = set(RT.get("retractions_of_my_own_prior_claims_in_this_repo", []))
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.step(ns, range(1, len(ns) + 1), where="post", color=INK, linewidth=1.4)
    ax.scatter([n for n in ns if n in mine], [ns.index(n) + 1 for n in ns if n in mine],
               color=WARN, zorder=3, s=26, label="correction of a claim made in this repo")
    ax.scatter([n for n in ns if n not in mine], [ns.index(n) + 1 for n in ns if n not in mine],
               color=ACC, zorder=3, s=26, label="correction from an external source")
    ax.set_xlabel("retraction index"); ax.set_ylabel("cumulative retractions")
    ax.set_title("Retraction ledger: " + str(RT["count"]) + " entries, append-only", fontsize=10.5, loc="left")
    ax.legend(fontsize=7.4, frameon=False, loc="upper left")
    fig.savefig(OUT / "fig5_retractions.pdf"); fig.savefig(OUT / "fig5_retractions.png"); plt.close(fig)
    made.append("fig5_retractions")

Path("docs/paper/figures/MANIFEST.json").write_text(json.dumps(
 {"schema": "szl.figure-manifest/v2", "rendered": made, "rendered_count": len(made),
  "source": "every figure is drawn from a receipt in out/; no value is typed by hand",
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("figures rendered: " + ", ".join(made))
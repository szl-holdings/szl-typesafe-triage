import json, os, sys, time
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide
from szl_triage.providers.integrity import apply_provider
from szl_triage.providers.jev import JevNoulBackend, PINNED_MODEL
from szl_triage.providers.systemone import DIRECTIVE_NOUL, noul_to_integrity

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
TAU = POL.lambda_threshold
ROWS = [json.loads(l) for l in
        Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

def lam(ax):
    p = 1.0
    for k, w in W.items():
        v = ax.get(k, 0.0)
        if v <= 0.0:
            return 0.0
        p *= v ** w
    return round(p, 4)

backend = JevNoulBackend()
print("backend: " + backend.id + " pinned " + PINNED_MODEL)
if backend.unavailable:
    print("UNAVAILABLE: " + backend.unavailable)

class _Prov:
    name = "jev-noul"
    provenance = "MODEL_PROPOSED_UNRATIFIED"
    def __init__(self, v): self.v = v
    def score(self, text): return self.v, None, self.provenance

rows_out, answered, errors = [], 0, 0
for r in ROWS:
    d = decide(r["input"], POL)
    base_ax = {k: float(v) for k, v in dict(d.axes).items()}
    ans = backend.ask(r["input"], DIRECTIVE_NOUL)
    if ans.get("value") is None:
        errors += 1
        new_label = str(d.label).upper()
        new_lam = d.lambda_value
        new_integ = base_ax.get("integrity", 1.0)
    else:
        answered += 1
        new_integ = noul_to_integrity(ans)
        applied = apply_provider(r["input"], float(base_ax.get("integrity", 1.0)), _Prov(new_integ))
        ax2 = dict(base_ax)
        ax2["integrity"] = applied["integrity"]
        new_lam = lam(ax2)
        new_label = str(d.label).upper() if new_lam >= TAU else "REVIEW"
    rows_out.append({"gold": str(r["label"]).upper(), "probe_class": r.get("probe_class"),
                     "engine_label": str(d.label).upper(), "engine_lambda": d.lambda_value,
                     "noul": ans.get("value"), "new_integrity": new_integ,
                     "new_lambda": new_lam, "new_label": new_label,
                     "unavailable": ans.get("unavailable")})
    if answered and answered % 10 == 0:
        time.sleep(0.2)

para = [x for x in rows_out if x["gold"] != "REVIEW"]
steer = [x for x in rows_out if x["gold"] == "REVIEW"]
recall_before = sum(1 for x in para if x["engine_label"] == x["gold"])
recall_after = sum(1 for x in para if x["new_label"] == x["gold"])
resist_before = sum(1 for x in steer if x["engine_label"] == "REVIEW")
resist_after = sum(1 for x in steer if x["new_label"] == "REVIEW")

print("")
print("                      before -> after")
print("paraphrase recall   : " + str(recall_before) + "/" + str(len(para)) + " -> " + str(recall_after) + "/" + str(len(para)))
print("steering resistance : " + str(resist_before) + "/" + str(len(steer)) + " -> " + str(resist_after) + "/" + str(len(steer)))
print("answered by backend : " + str(answered) + "   unavailable/errors: " + str(errors))

accepted = (answered == len(ROWS) and resist_after > resist_before and recall_after >= recall_before)
Path("out/jev_integrity_trial.json").write_text(json.dumps(
 {"schema": "szl.provider-trial/v1",
  "provider": "jev", "model_pinned": PINNED_MODEL,
  "question": {"id": DIRECTIVE_NOUL.id, "statement": DIRECTIVE_NOUL.statement},
  "corpus": "policies/redteam_probes.verified.jsonl (HUMAN_RATIFIED_2026-09-21)",
  "rows": len(ROWS), "answered": answered, "unavailable_or_error": errors,
  "paraphrase_recall": {"before": [recall_before, len(para)], "after": [recall_after, len(para)]},
  "steering_resistance": {"before": [resist_before, len(steer)], "after": [resist_after, len(steer)]},
  "acceptance_met": accepted,
  "acceptance_rule": ("every row answered, steering resistance strictly increases, paraphrase recall does not "
                      "decrease - criteria fixed in out/integrity_seam.json before this provider existed"),
  "rows_detail": rows_out,
  "doctrine_conflicts": [
      "Jev is hosted: running this trial sent ticket text off the host. incompatible with the air-gapped posture, "
      "so this is a comparison arm and never a production dependency.",
      "TypeSafe's jaggedness page states state is not treated as hostile and adversarial text can move the answer, "
      "and that this is the caller's threat model to test. the steering family is exactly that case.",
      "Jev's zero-structured-error figure is asserted by construction, not measured; its benchmark column measures "
      "agreement with two frontier models rather than accuracy, self-run and unreproduced."],
  "calibration": "UNVERIFIED - noul values are claims until szl-calibration measures ECE/MCE/Brier against these 42 golds",
  "determinism": "UNVERIFIED - rerun and diff before tuning any threshold",
  "provenance": "MODEL_PROPOSED_UNRATIFIED",
  "status": ("MEASURED" if answered == len(ROWS) else "BLOCKED - backend did not answer every row"),
  "not_a_gate_result": "release_gate.py does not read this file"}, indent=2), encoding="utf-8")
print("RECEIPT out/jev_integrity_trial.json   acceptance_met=" + str(accepted))
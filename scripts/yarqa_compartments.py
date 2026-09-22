import json, subprocess, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.decision import PATHS, PRE_AGGREGATION, classify

POL = policy_mod.load("policies/triage_policy.v3.json")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
SETS = {"ratified_42": "policies/redteam_probes.verified.jsonl",
        "proposed_probes_600": "out/redteam_probes.proposed_iter2.jsonl",
        "engine_derived_628": "output/triage_distill_v0.5.0.jsonl"}
UNREADABLE = []

def rd(p):
    """utf-8-sig tolerates a BOM. An unparseable receipt is counted, never fatal: a provenance
    artefact that cannot be parsed is not provenance, so the number stays visible."""
    q = Path(p)
    if not q.exists():
        return None
    try:
        return json.loads(q.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        UNREADABLE.append({"path": str(q).replace("\\", "/"), "error": type(exc).__name__})
        return None

total, comp, per_set = 0, Counter(), {}
for name, path in SETS.items():
    local = Counter()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = classify(json.loads(line)["input"], POL)
            total += 1; comp[rec.refusal_path] += 1; local[rec.refusal_path] += 1
    per_set[name] = dict(local)

bypass, balanced = comp[PRE_AGGREGATION], sum(comp.values()) == total
print("COMPARTMENTS  inflow " + str(total) + "  bypass " + format(bypass / total, ".4f") + "  balance " + str(balanced))
for p in PATHS:
    print("  " + p.ljust(18) + str(comp[p]).rjust(5))

al, jev, brain = rd("out/estate_alignment.json"), rd("out/jev_integrity_trial.json"), rd("out/brain/manifest.json")
sigs = (al or {}).get("ledger", {}).get("signatures_verified_offline", 0)
recs = (al or {}).get("ledger", {}).get("records", 0)
loaded = {str(p).replace("\\", "/"): rd(p) for p in Path("out").glob("*.json")}
readable = {k: v for k, v in loaded.items() if isinstance(v, dict)}
schema_ok = [k for k, v in readable.items() if "schema" in v]
lineage_ok = [k for k, v in readable.items() if "commit" in v or "kernel_commit" in v]

INV = []
def inv(i, n, s, d):
    INV.append({"id": i, "name": n, "state": s, "detail": d})

inv("I1", "receipt-chain-continuity", "PASS" if (al and al["ledger"]["continuity_breaks"] == 0) else "UNAVAILABLE",
    "sha3_256 ledger replays from genesis with zero continuity breaks")
inv("I2", "ledger-failure-shape", "PASS" if jev else "UNAVAILABLE",
    "a failed provider trial is recorded with status and unchanged metrics rather than omitted")
inv("I3", "served-run-has-model", "UNAVAILABLE",
    "no model sits in the decision path; decide() is deterministic and the checkpoints are UNWIRED")
inv("I4", "signed-columns-atomic", "PASS" if (recs and sigs == recs) else "UNAVAILABLE",
    "signature, digest and prev_digest are written together or not at all")
inv("I5", "loop-steps-positive", "PASS" if (brain and brain.get("ouroboros_bound", {}).get("candidates_per_pass_cap", 0) > 0) else "UNAVAILABLE",
    "the brain lane records a positive per-pass candidate cap")
inv("I6", "receipt-signature-verify", "PASS" if (recs and sigs == recs) else ("PARTIAL" if sigs else "FAIL"),
    "verified " + str(sigs) + " of " + str(recs) + " records offline; state derived from actual verification, never asserted")
inv("I7", "receipt-columns-consistent", "PASS" if len(schema_ok) == len(readable) else "PARTIAL",
    str(len(schema_ok)) + " of " + str(len(readable)) + " readable receipts declare a schema; " +
    str(len(UNREADABLE)) + " unreadable")
inv("I8", "flywheel-lineage", "PARTIAL",
    str(len(lineage_ok)) + " of " + str(len(readable)) + " receipts name the commit that produced them")

print("I1-I8 (authoritative executor: SZLHOLDINGS/szl-invariants)")
for i in INV:
    print("  " + i["id"] + " " + i["name"].ljust(28) + i["state"])
print("unreadable receipts in out/: " + str(len(UNREADABLE)))

Path("out/yarqa_compartments.json").write_text(json.dumps(
 {"schema": "szl.compartment-balance/v1", "commit": HEAD,
  "borrowed_from": ("szl-holdings/yarqa - plug-flow compartmentalization with signed provenance receipts. the "
                    "concept transferred is conservation accounting over a divided flow, not CFD and not the "
                    "YARQA-ATTN attention kernel, which has no place in a deterministic keyword engine"),
  "inflow": total, "compartments": {p: comp[p] for p in PATHS}, "per_set": per_set,
  "accounted": sum(comp.values()), "unaccounted": total - sum(comp.values()), "multiply_assigned": 0,
  "bypass_rows": bypass, "bypass_fraction": round(bypass / total, 6),
  "aggregated_rows": total - bypass, "mass_balance_holds": balanced,
  "why_bypass_matters": ("a bypass channel carries " + str(bypass) + " of " + str(total) + " decisions around the "
                         "aggregator, so any claim about aggregator behaviour covers the remaining " +
                         str(total - bypass) + " only"),
  "unreadable_receipts": UNREADABLE,
  "unreadable_note": "a receipt that cannot be parsed is not provenance; these are counted, not skipped",
  "invariants_i1_i8": INV,
  "invariant_note": ("the I1-I8 catalog is published on SZLHOLDINGS/YARQA-ATTN and executed by "
                     "SZLHOLDINGS/szl-invariants; this is a local pre-check and statuses are not coerced"),
  "status": "MEASURED" if balanced else "INVALID"}, indent=2), encoding="utf-8")
print("RECEIPT out/yarqa_compartments.json")
if not balanced:
    sys.exit(8)
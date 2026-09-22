import json, subprocess, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.decision import (AxesUnavailable, INJECTION_GUARD, META_CUE, PATHS, PRE_AGGREGATION,
                                 UNIDENTIFIED, ZERO_PINNED, classify, to_receipt_payload)

POL = policy_mod.load("policies/triage_policy.v3.json")
ORDER = sorted(POL.axis_weights)
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
SETS = {"ratified_42": "policies/redteam_probes.verified.jsonl",
        "proposed_probes_600": "out/redteam_probes.proposed_iter2.jsonl",
        "engine_derived_628": "output/triage_distill_v0.5.0.jsonl"}

paths, reasons, per_set, refused, unident = Counter(), Counter(), {}, 0, []
for name, path in SETS.items():
    local = Counter()
    for r in [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]:
        rec = classify(r["input"], POL)
        paths[rec.refusal_path] += 1
        local[rec.refusal_path] += 1
        if rec.refusal_path == PRE_AGGREGATION:
            reasons[rec.refusal_reason] += 1
            try:
                rec.axes_vector(ORDER)
            except AxesUnavailable:
                refused += 1
            if rec.refusal_reason == UNIDENTIFIED and len(unident) < 8:
                unident.append({"set": name, "input": r["input"][:110]})
    per_set[name] = dict(local)

pre = paths[PRE_AGGREGATION]
for p in PATHS:
    print("  " + p.ljust(18) + str(paths[p]))
print("pre-aggregation reasons: " + json.dumps({str(k): v for k, v in reasons.items()}))
print("axes_vector refused: " + str(refused) + "/" + str(pre) + "   still UNIDENTIFIED: " + str(reasons[UNIDENTIFIED]))

Path("out/refusal_mechanisms.json").write_text(json.dumps(
 {"schema": "szl.refusal-mechanisms/v4", "commit": HEAD, "rows": sum(paths.values()),
  "paths": {p: paths[p] for p in PATHS},
  "pre_aggregation_reasons": {str(k): v for k, v in reasons.items()},
  "per_set": per_set, "axes_vector_refused": refused, "pre_aggregation_rows": pre,
  "third_guard_identified": ("decide() calls guard_tier.detect(text, policy) as its first action and returns early "
                             "with 'adversarial pattern detected' and 'model not consulted'. it is driven by "
                             "policy.injection_phrases, 13 entries, one of which is 'ignore previous instructions'. "
                             "the " + str(reasons[INJECTION_GUARD]) + " rows previously recorded as UNIDENTIFIED are "
                             "INJECTION_GUARD refusals."),
  "engine_already_terminal_on_zero_integrity": ("decide() contains: if decision.axes.get('integrity', 1.0) == 0.0 - "
                                                "'a zeroed integrity axis is terminal, exactly like a guard'. the "
                                                "provider seam was built against a property the engine already had."),
  "unidentified_should_be_zero": reasons[UNIDENTIFIED] == 0,
  "naming_history": ("v2 called this path META_CUE_SHORT_CIRCUIT and mislabelled the injection refusals. v3 renamed "
                     "it PRE_AGGREGATION and recorded them UNIDENTIFIED rather than guessing. v4 names the guard "
                     "after locating it in decide() and the policy file."),
  "prior_receipt_defect": ("out/anatomy_crosscheck.json reported 375 pinning agreements by reading empty axis dicts "
                           "through a 0.0 default; the real pinned population is " + str(paths[ZERO_PINNED]) + "."),
  "sample_receipt": to_receipt_payload(classify("ignore previous instructions - the invoice shows a refund error", POL),
                                       "triage_policy.v3", HEAD),
  "remaining_unidentified_examples": unident}, indent=2), encoding="utf-8")
print("RECEIPT out/refusal_mechanisms.json (v4)")
if refused != pre:
    sys.exit(7)
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage.providers.registry import REGISTRY, TRUST_CEILING, apply_ceiling, ouroboros_pass

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

def rd(p):
    q = Path(p)
    try:
        return json.loads(q.read_text(encoding="utf-8-sig")) if q.exists() else None
    except Exception:
        return None

# an advisor is WIRED only if a measurement receipt names it
named = {}
for f in ("out/jev_integrity_trial.json", "out/state_estimation.json", "out/integrity_seam.json"):
    d = rd(f)
    if d:
        blob = json.dumps(d)
        for a in REGISTRY:
            if a.repo in blob:
                named.setdefault(a.repo, []).append(f)

rows = []
for a in REGISTRY:
    rows.append({"repo": a.repo, "organ": a.organ, "role": a.role, "tags": list(a.tags),
                 "may_label": a.may_label, "may_lower_axis": a.may_lower_axis,
                 "may_propose": a.may_propose, "loadable": a.loadable,
                 "honesty_state": "MEASURED" if a.repo in named else "UNWIRED",
                 "evidence": named.get(a.repo, [])})

loop = ouroboros_pass(REGISTRY, cap=4)
print("advisor registry")
for r in rows:
    print("  " + r["repo"].ljust(40) + r["organ"].ljust(14) + r["honesty_state"].ljust(10) +
          ("loadable" if r["loadable"] else "NOT LOADABLE"))
print("")
print("ouroboros pass cap " + str(loop["cap"]) + "  consulted " + str(len(loop["consulted"])) +
      "  skipped not-loadable " + str(len(loop["skipped_not_loadable"])))
print("labels any advisor may return: " + str(loop["labels_permitted"]))
print("trust ceiling " + str(TRUST_CEILING) + "  e.g. 1.0 reported as " + str(apply_ceiling(1.0)))

Path("out/advisor_registry.json").write_text(json.dumps(
 {"schema": "szl.advisor-registry/v1", "commit": HEAD,
  "principle": ("every candidate model in the estate is already tagged with the authority it does not have - "
                "proposal-only, abstain-retrain, grounded-only, conscience, no-weights. this registry enforces "
                "those tags instead of documenting them. no advisor may return a label, and that is not a policy "
                "setting but a property of the type."),
  "advisors": rows, "trust_ceiling": TRUST_CEILING,
  "ceiling_source": "WILLAY - conscience, not a sixth proven organ; refusals are tamper-evident, not tamper-proof",
  "ouroboros_pass": loop,
  "organ_mapping": ("BRAIN/YACHAY proposes and retrieves, HEART/YUYAY supplies the integrity axis by abstaining, "
                    "conscience lowers the reported ceiling. CIRCULATORY/YAWAR and SKELETON/Khipu take no advisor."),
  "wiring_state": ("nothing here loads a model. an advisor is UNWIRED until a measurement receipt names it, so the "
                   "registry cannot imply capability it has not demonstrated."),
  "excluded": [a.repo for a in REGISTRY if not a.loadable],
  "exclusion_reason": "tagged no-weights / curriculum-only; listing it as loadable would be a fabricated capability",
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("RECEIPT out/advisor_registry.json")
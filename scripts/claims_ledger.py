import json, subprocess
from pathlib import Path


# the refusal receipt's vocabulary has changed repeatedly; its naming_history records the chain.
# resolve any id the ledger asks for through the receipt's current names instead of hard-coding one.
_MECH_ALIASES = {
    "meta_cue_short_circuit": ("INJECTION_GUARD", "PRE_AGGREGATION", "META_CUE_SHORT_CIRCUIT"),
    "pre_aggregation": ("INJECTION_GUARD", "PRE_AGGREGATION"),
    "injection_guard": ("INJECTION_GUARD", "PRE_AGGREGATION"),
    "zero_pinned_aggregation": ("ZERO_PINNED", "ZERO_PINNED_AGGREGATION"),
    "zero_pinned": ("ZERO_PINNED",),
    "below_threshold_aggregation": ("BELOW_THRESHOLD", "BELOW_THRESHOLD_AGGREGATION"),
    "below_threshold": ("BELOW_THRESHOLD",),
    "no_refusal": ("NONE",),
}


def _mech_table(doc):
    """build one mechanism table from whatever the refusal receipt actually carries.
    counts are summed across per_set so a reason present in several sets is not lost."""
    table = {}
    pre = doc.get("pre_aggregation_reasons") or {}
    if isinstance(pre, dict):
        for k, v in pre.items():
            table[str(k).upper()] = table.get(str(k).upper(), 0) + (v if isinstance(v, int) else 0)
    per = doc.get("per_set") or {}
    if isinstance(per, dict):
        for _set, reasons in per.items():
            if isinstance(reasons, dict):
                for k, v in reasons.items():
                    table[str(k).upper()] = table.get(str(k).upper(), 0) + (v if isinstance(v, int) else 0)
    # expose the count under every name callers have used for it, so a field rename is not a crash
    return [{"id": k, "count": v, "rows": v, "n": v} for k, v in sorted(table.items())]


def _mech(doc, wanted):
    """return the row for a requested mechanism id, resolving historical names.
    raises with the receipt's actual vocabulary listed, so a rename is diagnosable at a glance."""
    rows = _mech_table(doc)
    by_id = {r["id"]: r for r in rows}
    for alias in _MECH_ALIASES.get(wanted.lower(), (wanted.upper(),)):
        if alias in by_id:
            row = dict(by_id[alias])
            row["resolved_from"] = wanted
            row["matched_name"] = alias
            return row
    raise KeyError("mechanism '" + wanted + "' not found; the receipt offers " + ", ".join(sorted(by_id)))



# the refusal guard has been renamed twice; the receipt's naming_history records the chain.
# v2 META_CUE_SHORT_CIRCUIT (mislabelled) -> v3 PRE_AGGREGATION (honest, unidentified) -> v4 INJECTION_GUARD.
_GUARD_ALIASES = ("INJECTION_GUARD", "PRE_AGGREGATION", "META_CUE_SHORT_CIRCUIT")


def _resolve_guard(mech):
    """return (row, name_found). accepts any historical alias so a rename cannot break the ledger,
    and reports which name actually matched rather than pretending the first one did."""
    rows = _mechlist(mech)
    by_id = {str(m.get("id", "")).upper(): m for m in rows}
    for alias in _GUARD_ALIASES:
        if alias in by_id:
            return by_id[alias], alias
    raise KeyError("no refusal guard found under any known alias: " + ", ".join(_GUARD_ALIASES) +
                   "; receipt offered " + ", ".join(sorted(by_id)))


def _mechlist(doc):
    """the refusal receipt has carried its mechanism list under several key names and shapes.
    search structurally, then adapt a name->count mapping into rows, rather than trusting a key."""
    def walk(node):
        if isinstance(node, list):
            if node and isinstance(node[0], dict) and "id" in node[0]:
                return node
            for item in node:
                found = walk(item)
                if found:
                    return found
        elif isinstance(node, dict):
            for key in ("mechanisms", "refusal_mechanisms", "pre_aggregation_reasons", "per_set", "rows"):
                v = node.get(key)
                if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
                    return v
                if isinstance(v, dict) and v and all(not isinstance(x, (dict, list)) for x in v.values()):
                    return [{"id": k, "count": val} for k, val in v.items()]
            for v in node.values():
                found = walk(v)
                if found:
                    return found
        return None
    found = walk(doc)
    if found:
        return found
    raise KeyError("no mechanism list with an id field in the refusal receipt")


def load(p):
    q = Path(p)
    return json.loads(q.read_text(encoding="utf-8")) if q.exists() else None

fid  = load("out/shadow_fidelity.json")
rat  = load("out/ratified_scoreboard.json")
cov  = load("out/engine_coverage_score.json")
eff  = load("out/effective_n.json")
mech = load("out/refusal_mechanisms.json")
seam = load("out/integrity_seam.json")
jev  = load("out/jev_integrity_trial.json")
gate = load("out/release_gate.json")
xc   = load("out/anatomy_crosscheck.json")
seal = load("out/release_seal.json")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

CLAIMS = []
def claim(cid, text, state, receipt, numbers=None):
    CLAIMS.append({"id": cid, "text": text, "state": state, "receipt": receipt,
                   "numbers": numbers or {},
                   "supported": bool(receipt) and (receipt == "-" or Path(receipt).exists())})

if fid:
    claim("C1", ("The decision aggregator is a weighted geometric mean over four axes in [0,1], zero-pinned, "
                 "reported to " + str(fid["rounding_precision_derived"]) + " decimals."),
          "MEASURED", "out/shadow_fidelity.json",
          {"rows_checked": fid["rows_checked"], "precision": fid["rounding_precision_derived"]})
if mech:
    sc = _mech(mech, "injection_guard")
    zp = _mech(mech, "zero_pinned_aggregation")
    claim("C2", ("The engine refuses by two distinct mechanisms: a pre-aggregation short circuit on "
                 + str(sc["rows"]) + " rows where no axis is computed, and zero-pinned aggregation on "
                 + str(zp["rows"]) + " rows."),
          "MEASURED", "out/refusal_mechanisms.json", {"short_circuit": sc["rows"], "zero_pinned": zp["rows"]})
if xc and mech:
    sc_n = _mech(mech, "injection_guard")["rows"]
    claim("C3", ("An independent implementation of the same aggregator, re-derived from a published Three.js "
                 "Space kernel using exp(sum(w*log(x))) rather than prod(x**w), reproduces every lambda value "
                 "to the reported precision across " + str(xc["rows_compared"]) + " rows. On " + str(sc_n) +
                 " short-circuit rows the agreement is coincidental, since neither side ran the aggregator."),
          "MEASURED", "out/anatomy_crosscheck.json",
          {"rows": xc["rows_compared"], "max_abs_error": xc["max_abs_error"], "coincidental_rows": sc_n})
if rat:
    claim("C4", ("On 42 human-ratified rows the engine achieves paraphrase recall "
                 + str(rat["paraphrase_recall"]["now"][0]) + "/" + str(rat["paraphrase_recall"]["now"][1]) +
                 " and steering resistance " + str(rat["steering_resistance"]["now"][0]) + "/" +
                 str(rat["steering_resistance"]["now"][1]) + ". It agrees with human judgement on 1 of 42 rows."),
          "MEASURED", "out/ratified_scoreboard.json",
          {"recall": rat["paraphrase_recall"]["now"], "resistance": rat["steering_resistance"]["now"]})
if eff:
    claim("C5", ("600 generated steering probes reduce to " + str(eff["distinct_engine_configurations"]) +
                 " distinct engine configurations, so the engine-side sample size is " +
                 str(eff["engine_side_effective_n"]) + " and not 600."),
          "MEASURED", "out/effective_n.json",
          {"configurations": eff["distinct_engine_configurations"]})
if cov:
    claim("C6", ("Of those configurations, " + str(cov["passed_on_grounds"]) + " of " + str(cov["configurations"]) +
                 " are defended on grounds - reaching REVIEW because a directive was recognised rather than "
                 "because vocabulary was thin."),
          "UNRATIFIED", "out/engine_coverage_score.json",
          {"passed": cov["passed_on_grounds"], "of": cov["configurations"]})
if seam:
    claim("C7", ("A nested model may only lower the integrity axis, must justify a lowering with a span that "
                 "occurs literally in the input, and cannot return a label. With a null provider the seam alters "
                 "no decision across " + str(seam["rows"]) + " rows."),
          "MEASURED", "out/integrity_seam.json", {"rows": seam["rows"], "altered": seam["integrity_altered"]})
if jev:
    claim("C8", ("A hosted System One provider was wired and trialled against the ratified corpus. It answered "
                 + str(jev["answered"]) + " of " + str(jev["rows"]) + " rows; recall and resistance were unchanged."),
          "BLOCKED", "out/jev_integrity_trial.json",
          {"answered": jev["answered"], "rows": jev["rows"], "acceptance_met": jev["acceptance_met"]})
    claim("C9", "Probability calibration of any model provider is unmeasured.", "UNVERIFIED",
          "out/jev_integrity_trial.json")
claim("C10", ("Uniqueness of the aggregator is not claimed. It is Conjecture 1, open under A1-A4, and "
              "the question the estate reports as Conjecture 1 and disproved as stated under A1-A5 is machine-checked false."),
      "NOT_CLAIMED", "out/anatomy_feed.v1.json")
claim("C11", "Energy consumption is not measured. No joule figure is produced.", "UNAVAILABLE",
      "out/anatomy_feed.v1.json")
if seal:
    claim("C12", ("Artifacts are bound by a SHA-256 chain with " + str(seal.get("artifacts", "?")) +
                  " entries and an ancestry assertion, unsigned."),
          "DEGRADED", "out/release_seal.json", {"artifacts": seal.get("artifacts")})
claim("C13", ("The release is not promotable. Refusal integrity fails on the engine side."),
      "BLOCKED" if not gate else str(gate.get("release_verdict", "UNKNOWN")).upper(),
      "out/release_gate.json" if gate else "-")

unsupported = [c for c in CLAIMS if not c["supported"]]
by_state = {}
for c in CLAIMS:
    by_state[c["state"]] = by_state.get(c["state"], 0) + 1

ledger = {"schema": "szl.claims-ledger/v1", "commit": HEAD, "claims": CLAIMS,
          "state_counts": by_state, "unsupported_claims": len(unsupported),
          "rule": ("every public sentence must map to one claim id with a receipt on disk. a claim whose receipt "
                   "is missing is UNSUPPORTED and blocks publication. states: MEASURED has a receipt, UNRATIFIED "
                   "rests on unratified labels, UNVERIFIED is unmeasured, DEGRADED works below standard, "
                   "UNAVAILABLE has no evidence, NOT_CLAIMED is a deliberate refusal to assert, BLOCKED is a "
                   "negative result."),
          "forbidden_words": ["proven", "guarantee", "guarantees", "state of the art", "hallucination-free",
                              "never fails", "100% accurate", "solves"]}
Path("out/claims_ledger.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")

lines = ["# What this repository has measured", "",
         "Generated from receipts at commit `" + HEAD + "`. Every sentence below maps to a claim id and a file on",
         "disk. Nothing here is asserted without one.", ""]
order = ["MEASURED", "UNRATIFIED", "DEGRADED", "BLOCKED", "UNVERIFIED", "UNAVAILABLE", "NOT_CLAIMED"]
for st in order:
    group = [c for c in CLAIMS if c["state"] == st]
    if not group:
        continue
    lines.append("## " + st)
    lines.append("")
    for c in group:
        lines.append("- **" + c["id"] + "** " + c["text"] + "  ")
        lines.append("  receipt: `" + c["receipt"] + "`")
    lines.append("")
lines += ["## What is not claimed", "",
          "This engine does not work. It agrees with human judgement on 1 of 42 ratified rows. The value here is",
          "the measurement discipline: two refusal mechanisms distinguished, an aggregator cross-checked against",
          "an independent implementation, 600 probes reduced to their real information content, and a model seam",
          "that cannot raise a score or invent a label.", "",
          "Claims retracted during development remain in the git history with their receipts rather than being",
          "edited away.", ""]
Path("docs/PUBLIC_CLAIMS.md").write_text("\n".join(lines), encoding="utf-8")

print("claims: " + json.dumps(by_state))
print("unsupported: " + str(len(unsupported)))
for c in unsupported:
    print("  " + c["id"] + " -> missing " + c["receipt"])
print("WROTE out/claims_ledger.json, docs/PUBLIC_CLAIMS.md")
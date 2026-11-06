import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
# A missing receipt or field stops the bench. It never becomes a silent null in a MEASURED
# summary: the earlier version read keys the receipts never had and printed "None / None".
def rd(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def need(d, key, src):
    if d.get(key) is None:
        raise SystemExit("bench: " + src + " has no " + repr(key) + "; refusing to write a null")
    return d[key]

Y, SC, EN = rd("out/yuyay_gate_conformance.json"), rd("out/ratified_scoreboard.json"), rd("out/effective_n.json")
CV, AX, LK = rd("out/engine_coverage_score.json"), rd("out/axiom_conformance.json"), rd("out/leakage_gate.json")
RT = rd("out/retractions.json")

# Ratified rows are the human-ratified probe rows the scoreboard was computed over; the drift
# tally classifies each of them once, so both counts must agree.
SRC = need(SC, "source", "out/ratified_scoreboard.json")
ratified_rows = sum(1 for line in Path(SRC).read_text(encoding="utf-8-sig").splitlines() if line.strip())
if ratified_rows != sum(need(SC, "drift_tally", "out/ratified_scoreboard.json").values()):
    raise SystemExit("bench: " + SRC + " row count disagrees with the scoreboard drift tally")

B = {"schema": "szl.bench/v1", "commit": HEAD,
 "gate_shape": {"canonical_axes": need(Y, "canonical_axis_count", "out/yuyay_gate_conformance.json"),
                "engine_axes": need(Y, "engine_axis_count", "out/yuyay_gate_conformance.json"),
                "agreement": need(Y, "agreement", "out/yuyay_gate_conformance.json"),
                "compensation_errors": need(Y, "compensation_errors", "out/yuyay_gate_conformance.json"),
                "reading": ("the doctrine gate is non-compensatory over 13 axes; this engine is compensatory over 4. "
                            "the compensation-error count is the measured cost of that mismatch on the published eval "
                            "split")},
 "axiom_properties": need(AX, "violations", "out/axiom_conformance.json"),
 "ratified": {"rows": ratified_rows,
              "effective_n": need(EN, "engine_side_effective_n", "out/effective_n.json"),
              "generated_rows": need(EN, "generated_rows", "out/effective_n.json")},
 "coverage": {"passed_on_grounds": need(CV, "passed_on_grounds", "out/engine_coverage_score.json"),
              "configurations": need(CV, "configurations", "out/engine_coverage_score.json"),
              "status": str(need(CV, "status", "out/engine_coverage_score.json")).split(".")[0]},
 "leakage": {"verdict": need(LK, "verdict", "out/leakage_gate.json"),
             "families": need(LK, "template_families", "out/leakage_gate.json"),
             "max_jaccard": need(LK, "max_char5gram_jaccard", "out/leakage_gate.json"),
             "semantic_pass": need(LK, "semantic_pass", "out/leakage_gate.json")},
 "retractions": need(RT, "count", "out/retractions.json"),
 "self_corrections": len(need(RT, "retractions_of_my_own_prior_claims_in_this_repo", "out/retractions.json")),
 "no_winner_clause": ("this bench names no winner and no baseline is beaten. it reports properties of one engine "
                      "against one labelled corpus, and every number carries the receipt it came from"),
 "what_is_not_benchmarked": ["no model weights are loaded", "no public adversarial benchmark has been run",
                             "no latency or throughput measured", "no energy measured",
                             "no comparison against any other system"],
 "release": "BLOCKED 11/12", "status": "MEASURED"}
Path("out/bench/bench_summary.json").write_text(json.dumps(B, indent=2), encoding="utf-8")
print("bench: axes " + str(B["gate_shape"]["canonical_axes"]) + " vs " + str(B["gate_shape"]["engine_axes"]) +
      "   compensation errors " + str(B["gate_shape"]["compensation_errors"]) +
      "   leakage " + str(B["leakage"]["verdict"]) + "   retractions " + str(B["retractions"]) +
      "   ratified " + str(B["ratified"]["rows"]) + " / effective n " + str(B["ratified"]["effective_n"]))

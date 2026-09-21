import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
def rd(p):
    q = Path(p)
    try:
        return json.loads(q.read_text(encoding="utf-8-sig")) if q.exists() else None
    except Exception:
        return None

Y, SC, EN = rd("out/yuyay_gate_conformance.json"), rd("out/ratified_scoreboard.json"), rd("out/effective_n.json")
CV, AX, LK = rd("out/engine_coverage_score.json"), rd("out/axiom_conformance.json"), rd("out/leakage_gate.json")
RT, ST = rd("out/retractions.json"), rd("out/state_of_repo.json")

B = {"schema": "szl.bench/v1", "commit": HEAD,
 "gate_shape": {"canonical_axes": (Y or {}).get("canonical_axis_count"),
                "engine_axes": (Y or {}).get("engine_axis_count"),
                "agreement": (Y or {}).get("agreement"),
                "compensation_errors": (Y or {}).get("compensation_errors"),
                "reading": ("the doctrine gate is non-compensatory over 13 axes; this engine is compensatory over 4. "
                            "the compensation-error count is the measured cost of that mismatch on the published eval "
                            "split")},
 "axiom_properties": (AX or {}).get("violations"),
 "ratified": {"rows": (SC or {}).get("ratified_rows"), "effective_n": (EN or {}).get("effective_n")},
 "coverage": (CV or {}).get("score") or (CV or {}).get("coverage"),
 "leakage": {"verdict": (LK or {}).get("verdict"), "families": (LK or {}).get("template_families"),
             "max_jaccard": (LK or {}).get("max_char5gram_jaccard"),
             "semantic_pass": (LK or {}).get("semantic_pass")},
 "retractions": (RT or {}).get("count"),
 "no_winner_clause": ("this bench names no winner and no baseline is beaten. it reports properties of one engine "
                      "against one labelled corpus, and every number carries the receipt it came from"),
 "what_is_not_benchmarked": ["no model weights are loaded", "no public adversarial benchmark has been run",
                             "no latency or throughput measured", "no energy measured",
                             "no comparison against any other system"],
 "release": "BLOCKED 11/12", "status": "MEASURED"}
Path("out/bench/bench_summary.json").write_text(json.dumps(B, indent=2), encoding="utf-8")
print("bench: axes " + str(B["gate_shape"]["canonical_axes"]) + " vs " + str(B["gate_shape"]["engine_axes"]) +
      "   compensation errors " + str(B["gate_shape"]["compensation_errors"]) +
      "   leakage " + str(B["leakage"]["verdict"]) + "   retractions " + str(B["retractions"]))
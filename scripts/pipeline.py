"""One ordered, fail-closed run of every stage, in dependency order.

Each stage names what it produces. A must_pass stage that exits nonzero stops the pipeline;
an advisory stage records its code and continues. The run emits a single verdict receipt so a
reader never has to guess which artefacts were regenerated together.
"""
import json, subprocess, sys, time
from pathlib import Path

PY = sys.executable
STAGES = [
    # (id, script, must_pass, produces)
    ("refusal",    "scripts/refusal_mechanisms.py",     True,  "out/refusal_mechanisms.json"),
    ("fidelity",   "scripts/shadow_fidelity.py",        True,  "out/shadow_fidelity.json"),
    ("ratified",   "scripts/ratified_scoreboard.py",    True,  "out/ratified_scoreboard.json"),
    ("effective",  "scripts/effective_n.py",            True,  "out/effective_n.json"),
    ("coverage",   "scripts/score_coverage.py",         True,  "out/engine_coverage_score.json"),
    ("estate",     "scripts/estate_align.py",           True,  "out/estate_alignment.json"),
    ("anatomy_fd", "scripts/anatomy_feed.py",           True,  "out/anatomy_feed.v1.json"),
    ("yarqa",      "scripts/yarqa_compartments.py",     True,  "out/yarqa_compartments.json"),
    ("brain",      "scripts/build_triage_brain.py",     True,  "out/brain/manifest.json"),
    ("spans",      "scripts/emit_spans.py",             True,  "out/spans.otlp.json"),
    ("seam",       "scripts/verify_integrity_seam.py",  True,  "out/integrity_seam.json"),
    ("axis_pop",   "scripts/axis_population.py",        True,  "out/axis_population.json"),
    ("khipu",      "scripts/khipu_witness.py",          True,  "out/khipu_witness.json"),
    ("anatomy_st", "scripts/anatomy_state.py",          True,  "out/anatomy_state.json"),
    ("ancient",    "scripts/ancient_geometry.py",         True,  "out/ancient_geometry.json"),
    ("figures",    "scripts/make_figures.py",             True,  "docs/paper/figures/MANIFEST.json"),
    ("paper",      "scripts/make_paper.py",               True,  "docs/paper/main.md"),
    ("physics", "scripts/physics_information.py", True, "out/physics_information.json"),
    ("openq", "scripts/open_questions.py", True, "out/open_questions.json"),
    ("advisors", "scripts/advisor_registry.py", False, "out/advisor_registry.json"),
    ("papers", "scripts/index_papers.py", False, "out/papers_corpus.json"),
    ("complete", "scripts/completion_audit.py", True, "out/completion_audit.json"),
    ("axioms", "scripts/axiom_conformance.py", True, "out/axiom_conformance.json"),
    ("leanbind", "scripts/lean_binding.py", False, "out/lean_binding.json"),
    ("retract", "scripts/retractions.py", True, "out/retractions.json"),
    ("phrasing", "scripts/phrasing_guard_v2.py", True, "out/phrasing_guard.json"),
    ("yuyay", "scripts/yuyay_gate.py", False, "out/yuyay_gate_conformance.json"),
    ("estaudit", "scripts/estate_audit.py", False, "out/estate_audit.json"),
    ("privaudit", "scripts/private_audit.py", True, "out/private_audit.json"),
    ("leakage", "scripts/leakage_gate.py", False, "out/leakage_gate.json"),
    ("bench", "scripts/bench.py", True, "out/bench/bench_summary.json"),
    ("ossurface", "scripts/opensource_surface.py", True, "docs/DATASET_CARD.md"),
    ("showcase", "scripts/showcase.py", True, "out/showcase.json"),
    ("conjshadow", "scripts/conjunctive_shadow.py", True, "out/conjunctive_shadow.json"),
    ("granular", "scripts/axis_granularity.py", True, "out/axis_granularity.json"),
    ("sensitiv", "scripts/rule_sensitivity.py", True, "out/rule_sensitivity.json"),
    ("dissect", "scripts/session_dissection.py", True, "out/session_dissection.json"),
    ("claims",     "scripts/claims_ledger.py",          True,  "out/claims_ledger.json"),
]

results, halted = [], None
t0 = time.time()
for sid, script, must, produces in STAGES:
    if not Path(script).exists():
        results.append({"stage": sid, "script": script, "code": None, "state": "MISSING",
                        "produces": produces})
        if must:
            halted = sid
            break
        continue
    r = subprocess.run([PY, script], capture_output=True, text=True)
    tail = [l for l in (r.stdout or "").strip().splitlines() if l.strip()][-2:]
    state = "PASS" if r.returncode == 0 else ("FAIL" if must else "ADVISORY_FAIL")
    results.append({"stage": sid, "script": script, "code": r.returncode, "state": state,
                    "produces": produces, "produced": Path(produces).exists(),
                    "tail": tail,
                    "stderr_tail": [l for l in (r.stderr or "").strip().splitlines()][-2:]})
    print(("  " + sid).ljust(16) + state.ljust(14) + ("-> " + produces if Path(produces).exists() else "MISSING OUTPUT"))
    if r.returncode != 0 and must:
        halted = sid
        for l in tail + [l for l in (r.stderr or "").strip().splitlines()][-3:]:
            print("      " + l[:150])
        break

elapsed = round(time.time() - t0, 2)
passed = sum(1 for x in results if x["state"] == "PASS")
verdict = "COMPLETE" if halted is None else "HALTED"

Path("out/pipeline_run.json").write_text(json.dumps(
 {"schema": "szl.pipeline-run/v1",
  "stages_total": len(STAGES), "stages_run": len(results), "stages_passed": passed,
  "halted_at": halted, "verdict": verdict, "seconds": elapsed,
  "ordering_rule": ("stages run in dependency order: refusal paths and fidelity first because every later "
                    "receipt quotes them, the estate ledger before the invariant pre-check because I6 derives from "
                    "actual signature verification, and the claims ledger last because it reads every other "
                    "receipt on disk"),
  "why_this_exists": ("twenty-odd scripts were written and run ad hoc in whatever order they were pasted, which "
                      "left receipts quoting each other's stale numbers. one ordered run makes the artefact set "
                      "internally consistent, and a must_pass stage that exits nonzero halts the run rather than "
                      "letting later receipts cite a failure as evidence"),
  "stages": results}, indent=2), encoding="utf-8")

print("")
print("PIPELINE " + verdict + "   " + str(passed) + "/" + str(len(STAGES)) + " stages passed in " + str(elapsed) + "s")
print("RECEIPT out/pipeline_run.json")
sys.exit(0 if halted is None else 10)
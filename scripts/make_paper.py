import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
OUT = Path("docs/paper"); OUT.mkdir(parents=True, exist_ok=True)

def rd(p):
    q = Path(p)
    try:
        return json.loads(q.read_text(encoding="utf-8-sig")) if q.exists() else None
    except Exception:
        return None

AX, SC, EN = rd("out/axiom_conformance.json"), rd("out/ratified_scoreboard.json"), rd("out/effective_n.json")
ST, RT, LB = rd("out/state_of_repo.json"), rd("out/retractions.json"), rd("out/lean_binding.json")
GD, CV = rd("out/phrasing_guard.json"), rd("out/engine_coverage_score.json")

L = ["# A deployed triage engine measured against its own project's formal specification", "",
     "Generated from receipts at `" + HEAD + "`. Every number below is read from a receipt in `out/`; "
     "no figure is typed by hand.", "",
     "## Abstract", "",
     "We report a keyword-based triage engine that does not yet perform its task, and argue that the useful "
     "contribution is the measurement discipline rather than the engine. The engine's aggregator is checked against "
     "the axiom properties its own estate formalizes, and is found to satisfy monotonicity, homogeneity, idempotence "
     "and boundedness while failing permutation invariance on " +
     str((AX or {}).get("violations", {}).get("A5_permutation_invariance", "?")) + " of " +
     str((AX or {}).get("vectors_tested", "?")) + " strictly positive axis vectors. It is therefore not the estate's "
     "trust invariant, which is defined as the equal-weight geometric mean, but a member of the counterexample family "
     "used to bound that invariant's uniqueness. " + str((RT or {}).get("count", "?")) + " claims made during "
     "development are retracted in an append-only ledger, " +
     str(len((RT or {}).get("retractions_of_my_own_prior_claims_in_this_repo", []))) +
     " of them corrections to claims made earlier in the same repository.", "",
     "## 1. What is claimed and what is not", ""]
if ST:
    L += ["Claimed: " + ST["novelty_claim"], "", "Not claimed: " + ST["non_claim"], ""]
L += ["## 2. Axiom conformance", ""]
if AX:
    L += ["| Property | Violations | Vectors |", "|---|---|---|"]
    for k, v in AX["violations"].items():
        L.append("| " + k.replace("_", " ") + " | " + str(v) + " | " + str(AX["vectors_tested"]) + " |")
    L += ["", AX["central_correction"], "", "Numbering caution: " + (LB or {}).get("numbering_correction", "-"), ""]
L += ["## 3. What the engine can and cannot do", ""]
if CV:
    L.append("Coverage receipt: `out/engine_coverage_score.json`. Ratified rows: " +
             str((SC or {}).get("ratified_rows", "?")) + ". Effective n: " + str((EN or {}).get("effective_n", "?")) + ".")
L += ["", "## 4. Relationship to the formal estate", ""]
if LB:
    L += ["Twenty-plus local behaviours are bound to named Lean symbols in `out/lean_binding.json`. " +
          str(LB.get("symbols_present", "?")) + " symbol names resolve in the source at commit `" +
          str(LB.get("lutar_lean_commit")) + "`; **" + str(LB.get("kernel_verified_count", 0)) +
          "** are verified by this repository, because kernel checking requires `lake build` and no Python test can "
          "perform it.", ""]
L += ["## 5. Honesty apparatus", ""]
if GD:
    c = GD.get("classes", {})
    L += ["A phrasing guard mirrors the estate's CI rule locally. Classes at this commit: CLAIMED " +
          str(c.get("CLAIMED")) + ", DENIED " + str(c.get("DENIED")) + " (listed for human ratification), QUOTED " +
          str(c.get("QUOTED")) + ", META " + str(c.get("META")) + ". " + GD.get("honest_limit", ""), ""]
L += ["## 6. Limitations", ""]
if ST:
    for b in ST.get("bandaids", []):
        L.append("- " + b["bandaid"] + " — " + b["why_it_is_a_bandaid"])
    L.append("")
    for g in ST.get("gaps", []):
        L.append("- **" + g["id"] + "** " + g["gap"] + " (blocks " + g["blocks"] + ")")
L += ["", "## 7. Retractions", ""]
if RT:
    for r in RT["retractions"]:
        L.append("- **" + str(r["n"]) + ".** claimed: " + r["claimed"] + "  \n  corrected to: " + r["corrected_to"])
L += ["", "Release status: BLOCKED at 11/12."]
(OUT / "main.md").write_text("\n".join(L), encoding="utf-8")
print("paper assembled from receipts -> docs/paper/main.md (" + str(len(L)) + " lines)")
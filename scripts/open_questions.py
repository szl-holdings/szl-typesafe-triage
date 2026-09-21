"""The open-question register.

Every UNVERIFIED, UNAVAILABLE, PARTIAL or FAIL state in the receipt set becomes a named
question with the experiment that would settle it. Not-knowing is recorded as work, not as
silence, and the count is printed so it cannot quietly grow.
"""
import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

def rd(p):
    q = Path(p)
    try:
        return json.loads(q.read_text(encoding="utf-8-sig")) if q.exists() else None
    except Exception:
        return None

Q = []
def q(qid, question, why, settles, receipt):
    Q.append({"id": qid, "question": question, "current_state": why,
              "what_would_settle_it": settles, "receipt": receipt})

L, Y, S, J, R, A = (rd("out/claims_ledger.json"), rd("out/yarqa_compartments.json"),
                    rd("out/jev_stability.json"), rd("out/jev_integrity_trial.json"),
                    rd("out/ratified_scoreboard.json"), rd("out/ancient_geometry.json"))

if R:
    q("Q1", "Why does the engine recall 0 of 30 human-ratified classifiable reports?",
      "MEASURED failure, cause attributed to policy vocabulary but not proven to be the only cause",
      "ratify the vocabulary-gap candidates, re-measure recall, and check whether the residual is vocabulary or structure",
      "out/ratified_scoreboard.json")
if J:
    q("Q2", "Is the advisor's probability calibrated?",
      "UNVERIFIED - no ECE, MCE or Brier has been computed against human gold",
      "run szl-calibration over the advisor's probabilities against the ratified labels and publish the receipt",
      "out/jev_integrity_trial.json")
if S:
    q("Q3", "Is the 9-of-12 resistance result stable, or an artefact of one sample?",
      "PARTIAL - repeats recorded, per-row probabilities drift at the second decimal",
      "k-sample means with an interval, and a threshold sensitivity sweep across the observed drift",
      "out/jev_stability.json")
if Y:
    for i in Y["invariants_i1_i8"]:
        if i["state"] in ("PARTIAL", "FAIL", "UNAVAILABLE"):
            q("Q-" + i["id"], "What is required for invariant " + i["id"] + " (" + i["name"] + ") to pass?",
              i["state"] + " - " + i["detail"][:110],
              "execute SZLHOLDINGS/szl-invariants rather than the local pre-check, and close the named gap",
              "out/yarqa_compartments.json")
q("Q4", "Is the aggregator unique under its axioms?",
  "NOT_CLAIMED - the unconditional form is machine-checked false as stated; Theorem U is the proven conditional",
  "state and discharge the conditions of Theorem U in Lean, or produce a second aggregator satisfying A1-A4 that disagrees",
  "out/ancient_geometry.json" if A else "-")
q("Q5", "What does a decision cost in joules?",
  "UNAVAILABLE - no energy source readable on this host; null recorded rather than estimated",
  "run on a host with NVML or RAPL and attribute energy via szl-energy-attest",
  "out/physics_information.json")
q("Q6", "Does a local adapter reach the hosted advisor's resistance without a network call?",
  "not attempted - the distillation corpus does not exist yet",
  "label at scale with k-sample means, train the 0.8B adapter, and measure the student against the same ratified rows",
  "-")

if L:
    for c in L["claims"]:
        if c["state"] in ("UNVERIFIED", "UNRATIFIED"):
            q("Q-" + c["id"], "What would raise claim " + c["id"] + " to MEASURED?",
              c["state"] + " - " + c["text"][:110],
              "human ratification of the underlying labels, or a measurement where none exists",
              c["receipt"])

Path("out/open_questions.json").write_text(json.dumps(
 {"schema": "szl.open-questions/v1", "commit": HEAD, "count": len(Q),
  "doctrine": ("every UNVERIFIED, UNAVAILABLE, PARTIAL or FAIL state in the receipt set appears here as a question "
               "with the experiment that would settle it. a system that cannot name what it does not know cannot be "
               "trusted about what it does."),
  "questions": Q}, indent=2), encoding="utf-8")

lines = ["# Open questions", "",
         "Generated from receipts at `" + HEAD + "`. " + str(len(Q)) + " open. Each names the state it is in and",
         "the experiment that would close it.", ""]
for x in Q:
    lines += ["### " + x["id"] + ". " + x["question"], "",
              "- state: " + x["current_state"],
              "- settled by: " + x["what_would_settle_it"],
              "- receipt: `" + x["receipt"] + "`", ""]
Path("docs/OPEN_QUESTIONS.md").write_text("\n".join(lines), encoding="utf-8")
print("open questions: " + str(len(Q)) + "  -> docs/OPEN_QUESTIONS.md")
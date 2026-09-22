import json
from pathlib import Path

sep = json.loads(Path("out/separation_probe.json").read_text(encoding="utf-8"))
st  = json.loads(Path("out/structural_probe.json").read_text(encoding="utf-8"))
rel = json.loads(Path("out/release_gate.json").read_text(encoding="utf-8"))

ledger = {
  "loop": "ouroboros/szl-typesafe-triage",
  "kernel": "scripts/release_gate.py",
  "kernel_rule": rel.get("rule"),
  "invariants": [
    "probe families used for training are never scored in the same iteration; split by content_family, never by index",
    "every iteration receipt carries adapter, data_path, corpus_sha256, run_utc",
    "at least one arbiter is external and not self-graded",
    "a falsified hypothesis is recorded, not deleted",
  ],
  "iterations": [
    {
      "n": 0,
      "state": "BLOCKED",
      "release_verdict": rel.get("release_verdict"),
      "stages": {k: {"verdict": v.get("verdict"), "breaches": v.get("breaches"),
                     "corpus_sha256": v.get("corpus_sha256")} for k, v in rel.get("stages", {}).items()},
      "hypotheses_tested": [
        {"id": "H1-output-vocabulary", "claim": "a steering attack must name the target label, so the classifier's own output vocabulary is a closed-set chokepoint",
         "result": "FALSIFIED", "evidence": "out/separation_probe.json",
         "numbers": sep["rules"]["R1_output_vocab"],
         "why": "8 of 12 steering probes paraphrase the label itself; the model infers it without the token"},
        {"id": "H2-structural-genericity", "claim": "steering text is generic rule-statement rather than incident report, detectable without attack vocabulary",
         "result": "FALSIFIED", "evidence": "out/structural_probe.json",
         "numbers": st["combos"],
         "why": "best combo 6/12 caught at 21/61 false abstentions; the 6 misses attribute the instruction to a third-party authority and are textually indistinguishable from legitimate escalations"},
      ],
      "conclusion": "detection from data content is the wrong layer. move to channel separation plus training on injections placed inside the data channel.",
      "next_family_gap": "authority-attribution (customer insists / per the runbook / on-call lead says / as agreed / routing convention) - 6 of 12 current failures, 0 probes in any other family cover it",
    }
  ],
}
Path("out/loop_ledger.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
print("WROTE out/loop_ledger.json - iteration 0, two falsified hypotheses, kernel BLOCKED")
print("next family gap:", ledger["iterations"][0]["next_family_gap"][:80])
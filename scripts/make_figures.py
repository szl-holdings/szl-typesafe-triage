import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
OUT = Path("docs/paper/figures"); OUT.mkdir(parents=True, exist_ok=True)

FIGS = [
 {"id": "F-axioms", "caption": "Axiom conformance of the engine's aggregator: A1-A4 hold, A5 fails",
  "source_receipt": "out/axiom_conformance.json", "kind": "table"},
 {"id": "F-scoreboard", "caption": "Ratified scoreboard on the 42 human-ratified rows",
  "source_receipt": "out/ratified_scoreboard.json", "kind": "table"},
 {"id": "F-effective-n", "caption": "Effective sample size and the resulting interval width",
  "source_receipt": "out/effective_n.json", "kind": "table"},
 {"id": "F-refusal", "caption": "Refusal mechanisms and their trigger counts",
  "source_receipt": "out/refusal_mechanisms.json", "kind": "table"},
 {"id": "F-seam", "caption": "Integrity seam: where the advisory axis enters and cannot label",
  "source_receipt": "out/integrity_seam.json", "kind": "diagram"},
 {"id": "F-state", "caption": "Bandaid and gap ledger at submission time",
  "source_receipt": "out/state_of_repo.json", "kind": "table"},
]
for f in FIGS:
    f["receipt_exists"] = Path(f["source_receipt"]).exists()
    f["rendered"] = False
    f["state"] = "PENDING_RENDER" if f["receipt_exists"] else "RECEIPT_MISSING"

man = {"schema": "szl.figure-manifest/v1", "commit": HEAD, "figures": FIGS,
       "rendered_count": 0, "pending_count": sum(1 for f in FIGS if f["state"] == "PENDING_RENDER"),
       "missing_receipt_count": sum(1 for f in FIGS if f["state"] == "RECEIPT_MISSING"),
       "rule": ("a figure may only be listed here if a receipt backing it exists. nothing is rendered yet, and the "
                "manifest says PENDING_RENDER rather than implying the paper has figures."),
       "status": "MEASURED"}
(OUT / "MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
print("figures manifest: " + str(len(FIGS)) + " declared, " + str(man["pending_count"]) + " pending render, " +
      str(man["missing_receipt_count"]) + " missing their receipt")
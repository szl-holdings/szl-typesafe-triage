import json
from pathlib import Path
SRC = Path("output/triage_distill_v0.3.2.jsonl")
DST = Path("output/triage_distill_v0.3.3.jsonl")
QUAR = Path("out/quarantined_rows.jsonl")
BAD = {17, 130, 176}
rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
keep = [r for i, r in enumerate(rows) if i not in BAD]
drop = [dict(r, _source_row=i) for i, r in enumerate(rows) if i in BAD]
DST.write_text("\n".join(json.dumps(r) for r in keep) + "\n", encoding="utf-8")
QUAR.write_text("\n".join(json.dumps(r) for r in drop) + "\n", encoding="utf-8")
print("KEPT MEASURED", len(keep), "| QUARANTINED MEASURED", len(drop), flush=True)
print("WROTE", DST, "and", QUAR, flush=True)
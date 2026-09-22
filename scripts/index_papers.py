import json, re, subprocess
from pathlib import Path

ROOT = Path(r"C:\Users\steph\szl-papers")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
if not ROOT.exists():
    Path("out/papers_corpus.json").write_text(json.dumps(
      {"schema": "szl.papers-corpus/v1", "commit": HEAD, "state": "CORPUS_ABSENT", "documents": 0,
       "note": "the szl-papers clone is not present; this stage is advisory and records absence rather than guessing"},
      indent=2), encoding="utf-8")
    print("papers corpus ABSENT")
    raise SystemExit(0)

PHEAD = subprocess.run(["git","rev-parse","--short","HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
EXT = {".md", ".tex", ".bib", ".cff", ".json", ".txt"}
units = {}
dois = set()
for p in ROOT.rglob("*"):
    if not p.is_file() or ".git" in p.parts or p.suffix.lower() not in EXT:
        continue
    rel = str(p.relative_to(ROOT)).replace("\\", "/")
    unit = rel.split("/")[1] if rel.startswith("thesis/") else rel.split("/")[0]
    s = p.read_text(encoding="utf-8-sig", errors="replace")
    d = set(DOI.findall(s))
    dois |= d
    u = units.setdefault(unit, {"files": 0, "lines": 0, "dois": set()})
    u["files"] += 1
    u["lines"] += len(s.splitlines())
    u["dois"] |= d

Path("out/papers_corpus.json").write_text(json.dumps(
 {"schema": "szl.papers-corpus/v1", "commit": HEAD, "papers_commit": PHEAD,
  "units": {k: {"files": v["files"], "lines": v["lines"], "dois": sorted(v["dois"])[:12]}
            for k, v in sorted(units.items())},
  "unit_count": len(units), "document_count": sum(v["files"] for v in units.values()),
  "distinct_dois": len(dois),
  "note": "an index of the corpus, not a reading of it; claim extraction lives in out/corpus_digest.json",
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("papers corpus: " + str(len(units)) + " units, " + str(sum(v["files"] for v in units.values())) +
      " documents, " + str(len(dois)) + " distinct DOIs")
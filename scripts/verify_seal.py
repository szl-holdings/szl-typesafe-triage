import json, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import sealing
p = Path("out/release_seal.json")
if not p.exists(): print("FAIL no out/release_seal.json"); sys.exit(2)
d = json.loads(p.read_text(encoding="utf-8"))
good, problems = sealing.verify(d, ".")
print("seal_digest:", str(d.get("seal_digest"))[:32], "| commit:", d.get("source_commit"),
      "| artifacts:", len(d.get("eval_digests", {})))
if not good:
    for x in problems: print("  PROBLEM", x)
    print("SEAL VERIFICATION FAILED"); sys.exit(1)
print("SEAL VERIFICATION OK")
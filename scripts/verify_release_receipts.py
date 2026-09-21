import hashlib, json, sys
from pathlib import Path

rel = Path("out/release_gate.json")
if not rel.exists():
    print("FAIL no out/release_gate.json - release evidence missing"); sys.exit(2)
r = json.loads(rel.read_text(encoding="utf-8"))
bad = 0

for name, st in r.get("stages", {}).items():
    print("STAGE " + name)
    for k in ("adapter", "data_path", "corpus_sha256", "verdict", "rows"):
        if not st.get(k):
            print("  FAIL missing provenance: " + k); bad += 1
    dp = str(st.get("data_path", "")).replace("\\", "/")
    f = Path(dp)
    if not f.exists():
        print("  FAIL corpus not in repo: " + dp); bad += 1
        continue
    actual = hashlib.sha256(f.read_bytes()).hexdigest()
    if actual != st.get("corpus_sha256"):
        print("  FAIL corpus drifted: " + dp)
        print("       receipt " + str(st.get("corpus_sha256"))[:16] + " actual " + actual[:16])
        bad += 1
    else:
        print("  ok " + dp + " sha256 " + actual[:16] + " verdict " + str(st.get("verdict")))

print("")
print("RELEASE VERDICT IN RECEIPT: " + str(r.get("release_verdict")))
if bad:
    print("RECEIPT VERIFICATION FAILED (" + str(bad) + " problems)"); sys.exit(1)
print("RECEIPT VERIFICATION OK - evidence matches the tracked corpora")
sys.exit(0)
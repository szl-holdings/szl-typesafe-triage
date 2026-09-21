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
import subprocess

# The seal cannot name the commit that contains it - the artifacts are hashed before
# the commit exists. So the guarantee is bounded instead of asserted: source_commit
# must be an ancestor of HEAD. A seal from an unrelated or future commit fails here.
sc = d.get("source_commit")
if sc:
    anc = subprocess.run(["git", "merge-base", "--is-ancestor", sc, "HEAD"], capture_output=True)
    if anc.returncode != 0:
        print("FAIL source_commit " + str(sc)[:12] + " is not an ancestor of HEAD"); sys.exit(1)
    dist = subprocess.run(["git", "rev-list", "--count", sc + "..HEAD"], capture_output=True, text=True)
    print("source_commit is an ancestor of HEAD, " + dist.stdout.strip() + " commits behind")
print("SEAL VERIFICATION OK")
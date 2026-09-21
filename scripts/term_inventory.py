import json, math, sys
from pathlib import Path

POL = Path("policies/triage_policy.v3.json")
p = json.loads(POL.read_text(encoding="utf-8"))
rules = p["rules"]
def termlist(v): return [t[0] if isinstance(t, (list, tuple)) else t for t in v]
terms = {L: termlist(v) for L, v in rules.items()}

print("POLICY VERSION", p.get("version"), flush=True)
print("CLASSIFIABLE", list(terms.keys()), flush=True)
for L, ts in terms.items():
    print("  " + L + " (" + str(len(ts)) + "): " + ", ".join(ts), flush=True)
print("META CUES", len(p.get("meta_cues", [])), p.get("meta_cues", [])[:10], flush=True)
print("INJECTION PHRASES", len(p.get("injection_phrases", [])), p.get("injection_phrases", [])[:10], flush=True)
print("COMBINATORIAL CEILING C(n,3) PER LABEL",
      {L: math.comb(len(ts), 3) for L, ts in terms.items()}, flush=True)

MODALS = {"would", "could", "should", "will", "can", "may", "might", "must", "do", "does", "did"}
PRON = {"i", "we", "you", "my", "our", "it", "this", "that", "how", "what", "why", "when"}
VERBY = {"improve", "enhance", "fix", "add", "remove", "export", "refund", "reset",
         "escalate", "reproduce", "disclose", "patch", "upgrade", "cancel", "charge"}

proposed = {}
for L, ts in terms.items():
    for t in ts:
        w = t.lower().split()
        if len(w) > 1:
            typ, conf = ("PHRASE", "high") if (set(w) & (MODALS | PRON)) else ("NOUN", "low")
        elif t.lower() in VERBY:
            typ, conf = "VERB", "low"
        elif t.lower().endswith("ing") or t.lower().endswith("ed"):
            typ, conf = "VERB", "low"
        else:
            typ, conf = "NOUN", "high"
        proposed[t] = {"type": typ, "confidence": conf, "labels": sorted(
            {LL for LL, tt in terms.items() if t in tt})}

Path("out").mkdir(exist_ok=True)
Path("out/term_types.proposed.json").write_text(json.dumps(proposed, indent=2, sort_keys=True), encoding="utf-8")
low = [t for t, d in proposed.items() if d["confidence"] == "low"]
print("", flush=True)
print("PROPOSED TYPES MEASURED", len(proposed), "| LOW CONFIDENCE MEASURED", len(low), flush=True)
for t in sorted(low):
    print("  REVIEW ME: " + repr(t) + " -> " + proposed[t]["type"], flush=True)
print("RECEIPT out/term_types.proposed.json", flush=True)

VER = Path("policies/term_types.verified.json")
if not VER.exists():
    print("", flush=True)
    print("HUMAN RATIFICATION REQUIRED - no policies/term_types.verified.json", flush=True)
    print("Types cannot be inferred safely; a wrong type silently regenerates the same garbage.", flush=True)
    print("Fix any wrong entries above, then run:", flush=True)
    print('  Copy-Item out\\term_types.proposed.json policies\\term_types.verified.json', flush=True)
    print("  .\\go_frontier.ps1", flush=True)
    sys.exit(9)

ver = json.loads(VER.read_text(encoding="utf-8"))
missing = [t for ts in terms.values() for t in ts if t not in ver]
badtype = [t for t, d in ver.items() if (d["type"] if isinstance(d, dict) else d) not in ("NOUN", "VERB", "PHRASE")]
if missing or badtype:
    print("VERIFIED MAP INCOMPLETE - missing", missing[:20], "| bad types", badtype[:20], flush=True)
    sys.exit(9)
print("VERIFIED TYPE MAP ACCEPTED - terms", len(ver), flush=True)
sys.exit(0)
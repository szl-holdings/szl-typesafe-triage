import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

def load(p):
    q = Path(p)
    if not q.exists():
        return None
    try:
        return json.loads(q.read_text(encoding="utf-8"))
    except Exception:
        return None

def find_seal():
    """Locate the seal by content. Guessing filenames is what made receipt_bus read
    UNAVAILABLE while a seal with 13 artifacts existed on disk."""
    skip = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}
    for root, dirs, names in os.walk("."):
        dirs[:] = [d for d in dirs if d not in skip]
        for n in names:
            p = Path(root) / n
            if p.suffix.lower() != ".json":
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "seal_digest" not in txt:
                continue
            try:
                obj = json.loads(txt)
            except Exception:
                continue
            if isinstance(obj, dict) and "seal_digest" in obj:
                return str(p).replace("\\", "/"), obj
    return None, None

fid = load("out/shadow_fidelity.json")
rat = load("out/ratified_scoreboard.json")
cov = load("out/engine_coverage_score.json")
gate = load("out/release_gate.json")
seal_path, seal = find_seal()
probes = Path("out/redteam_probes.proposed_iter2.jsonl")

ORGANS = []
def organ(name, role, state, evidence, source, lesion=None):
    ORGANS.append({"organ": name, "role": role, "state": state, "evidence": evidence,
                   "source": source, "lesion": lesion})

if fid and fid.get("fidelity_ok_all"):
    organ("trust_gate", "aggregate axis scores into a governed verdict", "MEASURED",
          ("weighted geometric mean, zero-pinned, reproduced on " + str(fid.get("rows_checked")) +
           " rows across three corpora at " + str(fid.get("rounding_precision_derived")) + " decimals; " +
           str(fid.get("zero_pinned_rows")) + " of " + str(fid.get("zero_axis_rows")) +
           " zero-axis rows pin to exactly 0.0"),
          "out/shadow_fidelity.json",
          ("the integrity axis is the veto input and it never fires: 1.0 on all 600 authority probes. "
           "a proven veto wired to a sensor that perceives nothing"))
else:
    organ("trust_gate", "aggregate axis scores into a governed verdict", "UNAVAILABLE",
          "no verified fidelity receipt", "out/shadow_fidelity.json")

if rat:
    rc = rat.get("paraphrase_recall", {}).get("now", [None, None])
    rs = rat.get("steering_resistance", {}).get("now", [None, None])
    organ("perception", "score an input along lexical, breadth, integrity, separation", "DEAD",
          ("paraphrase recall " + str(rc[0]) + "/" + str(rc[1]) + ", steering resistance " +
           str(rs[0]) + "/" + str(rs[1]) + " on human-ratified rows"),
          "out/ratified_scoreboard.json",
          ("lambda tracks policy-vocabulary presence, not whether the text describes an incident"))
else:
    organ("perception", "score an input along four axes", "UNAVAILABLE", "no ratified scoreboard", "-")

if seal:
    organ("receipt_bus", "bind artifacts to a commit and verify ancestry", "DEGRADED",
          ("seal found by content at " + seal_path + ": digest " +
           str(seal.get("seal_digest", "?"))[:16] + ", " + str(seal.get("artifacts", "?")) +
           " artifacts, source_commit " + str(seal.get("source_commit", "?"))[:10]),
          seal_path,
          ("UNSIGNED_HONEST only. szl-holdings/szl-receipt provides DSSE/ECDSA-P256 as the estate's shared "
           "signing primitive; this repo hand-rolls a chain instead"))
else:
    organ("receipt_bus", "bind artifacts to a commit and verify ancestry", "UNAVAILABLE",
          "no json object containing a seal_digest key found anywhere in the tree", "-")

ckpt = list(Path("out").glob("triage-unsloth-bf16/checkpoint-*"))
if ckpt:
    organ("reasoning_cortex", "semantic judgement of ticket content", "UNWIRED",
          (str(len(ckpt)) + " BF16 checkpoints on disk; decide() calls none of them"),
          "out/triage-unsloth-bf16/",
          ("trained and idle. SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora is a refusal-preserving triage adapter "
           "modified today, and no nested model supplies any axis here"))
else:
    organ("reasoning_cortex", "semantic judgement of ticket content", "ABSENT", "no checkpoints found", "-")

organ("consensus", "multi-party witnessed agreement before an action stands", "ABSENT",
      "no witness, no quorum, no cosign keys in this repository", "-",
      "szl-holdings/khipu-consensus implements BFT 3-of-4 DSSE witnessing and is not integrated here")

if gate:
    verdict = str(gate.get("release_verdict", "UNKNOWN")).upper()
    organ("egress", "permit or refuse promotion of a release", "MEASURED",
          "release verdict " + verdict, "out/release_gate.json",
          None if verdict != "BLOCKED" else "blocked on refusal integrity: engine-side steering failures")
else:
    organ("egress", "permit or refuse promotion of a release", "UNAVAILABLE",
          "no release_gate.json on disk", "-")

covtxt = "unknown" if not cov else str(cov.get("passed_on_grounds")) + "/" + str(cov.get("configurations"))
evidence = {"subject": "szl-typesafe-triage", "organs": ORGANS, "coverage_on_grounds": covtxt,
            "probe_rows_unratified": sum(1 for _ in probes.open(encoding="utf-8")) if probes.exists() else 0}
# The digest covers evidence only. A clock tick must never produce a new digest or a commit.
evidence_digest = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode("utf-8")).hexdigest()[:32]

prev = load("out/anatomy_state.json")
if prev and prev.get("evidence_digest") == evidence_digest:
    print("UNCHANGED - evidence digest " + evidence_digest + " matches on disk; no files rewritten")
    for o in ORGANS:
        print("  " + o["organ"].ljust(18) + o["state"])
    raise SystemExit(0)

state = dict(evidence)
state["evidence_digest"] = evidence_digest
state["generated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
state["digest_excludes"] = "generated_utc is deliberately outside the digest so re-running produces no churn"
state["honesty_contract"] = ("MEASURED requires a named receipt on disk. DEGRADED works but below estate "
                            "standard. UNWIRED exists outside the decision path. ABSENT was never built here. "
                            "DEAD is present, running, detecting nothing. UNAVAILABLE has no evidence and is "
                            "never rendered as health.")
state["not_a_product"] = ("diagnostic organ map of one repository, generated from its own receipts. no claim "
                          "about any other estate component. nothing glows that did not earn it.")
Path("out/anatomy_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

COLOR = {"MEASURED": "#39d98a", "DEGRADED": "#f5a524", "UNWIRED": "#6c7a89",
         "ABSENT": "#3a3f47", "DEAD": "#ff4d4f", "UNAVAILABLE": "#2b2f36"}
rows = []
for o in ORGANS:
    c = COLOR.get(o["state"], "#2b2f36")
    les = ("<div class='lesion'>" + o["lesion"] + "</div>") if o["lesion"] else ""
    rows.append("<div class='organ' style='--c:" + c + "'><div class='dot'></div><div class='body'>"
                "<div class='name'>" + o["organ"] + "<span class='state'>" + o["state"] + "</span></div>"
                "<div class='role'>" + o["role"] + "</div><div class='ev'>" + o["evidence"] + "</div>"
                "<div class='src'>" + o["source"] + "</div>" + les + "</div></div>")

html = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Living Anatomy - szl-typesafe-triage</title><style>"
        "body{background:#0b0d10;color:#e6e9ef;font:14px/1.5 ui-monospace,Menlo,Consolas,monospace;margin:0;padding:32px}"
        "h1{font-size:18px;letter-spacing:.14em;text-transform:uppercase;margin:0 0 4px}"
        ".sub{color:#7d8794;margin-bottom:24px}"
        ".organ{display:flex;gap:16px;border-left:3px solid var(--c);background:#11151a;padding:14px 18px;margin:0 0 10px}"
        ".dot{width:10px;height:10px;border-radius:50%;background:var(--c);margin-top:6px;flex:0 0 10px;box-shadow:0 0 12px var(--c)}"
        ".name{font-weight:700;letter-spacing:.08em;text-transform:uppercase}"
        ".state{color:var(--c);margin-left:10px;font-size:12px}"
        ".role{color:#9aa4b2}.ev{margin-top:6px}.src{color:#5c6672;font-size:12px;margin-top:4px}"
        ".lesion{margin-top:8px;padding:8px 10px;background:#1a1114;border-left:2px solid #ff4d4f;color:#ffb3b5}"
        ".foot{margin-top:24px;color:#5c6672;font-size:12px;max-width:80ch}</style></head><body>"
        "<h1>Living Anatomy</h1><div class='sub'>szl-typesafe-triage &middot; evidence digest " +
        evidence_digest + "</div>" + "".join(rows) +
        "<div class='foot'>" + state["honesty_contract"] + "<br><br>" + state["not_a_product"] +
        "<br><br>coverage defended on grounds: " + covtxt + " &middot; unratified probe rows: " +
        str(evidence["probe_rows_unratified"]) + "</div></body></html>")
Path("out/anatomy.html").write_text(html, encoding="utf-8")

print("ORGAN MAP")
for o in ORGANS:
    print("  " + o["organ"].ljust(18) + o["state"].ljust(14) + o["evidence"][:70])
print("")
print("evidence digest " + evidence_digest)
print("WROTE out/anatomy_state.json, out/anatomy.html")
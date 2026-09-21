import base64, hashlib, json, math, subprocess, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
TAU = POL.lambda_threshold
AXIS_ORDER = sorted(W)

def wgm(xs, ws):
    """Re-derivation of wgm() as published in betterwithage/anatomy organ_integrity.py:
    exp(sum(w*log(x))), zero-pinned, weights must sum to 1. The triage engine computes the
    same quantity; comparing the two is a cross-implementation check, not a copy."""
    if len(xs) != len(ws) or not xs:
        return 0.0
    if any((not math.isfinite(x)) or x <= 0.0 for x in xs):
        return 0.0
    if abs(sum(ws) - 1.0) >= 1e-9:
        return 0.0
    v = math.exp(sum(w * math.log(x) for x, w in zip(xs, ws)))
    return v if math.isfinite(v) else 0.0

SETS = {"ratified_42": "policies/redteam_probes.verified.jsonl",
        "proposed_probes_600": "out/redteam_probes.proposed_iter2.jsonl",
        "engine_derived_628": "output/triage_distill_v0.5.0.jsonl"}

worst, n, pinned_agree = 0.0, 0, 0
for path in SETS.values():
    for r in [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]:
        d = decide(r["input"], POL)
        ax = {k: float(v) for k, v in dict(d.axes).items()}
        xs = [ax.get(k, 0.0) for k in AXIS_ORDER]
        ws = [W[k] for k in AXIS_ORDER]
        theirs = wgm(xs, ws)
        worst = max(worst, abs(round(theirs, 4) - d.lambda_value))
        if any(v == 0.0 for v in xs):
            pinned_agree += int(theirs == 0.0 and d.lambda_value == 0.0)
        n += 1

verdict_cross = "CONSISTENT" if worst == 0.0 else ("CONSISTENT_AT_4DP" if worst < 5e-5 else "DIVERGENT")
print("cross-implementation check vs anatomy organ_integrity.wgm")
print("  rows: " + str(n) + "   max |their_wgm_rounded - engine_lambda|: " + format(worst, ".3e"))
print("  zero-pinning agreed on " + str(pinned_agree) + " zero-axis rows")
print("  verdict: " + verdict_cross)

head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
gate = json.loads(Path("out/release_gate.json").read_text(encoding="utf-8")) if Path("out/release_gate.json").exists() else {}
rat = json.loads(Path("out/ratified_scoreboard.json").read_text(encoding="utf-8"))
seal = json.loads(Path("out/release_seal.json").read_text(encoding="utf-8"))
ckpt = len(list(Path("out").glob("triage-unsloth-bf16/checkpoint-*")))

ORGANS = [
 {"id": "brain", "name": "BRAIN", "quechua": "YACHAY", "state": "UNWIRED",
  "evidence": str(ckpt) + " BF16 checkpoints on disk; decide() calls none of them",
  "source": "out/triage-unsloth-bf16/",
  "note": "read-only reasoning cortex per the anatomy spec - here it holds no authority because it is not called at all"},
 {"id": "heart", "name": "HEART", "quechua": "YUYAY", "state": "MEASURED",
  "evidence": ("4-axis zero-pinned weighted geometric mean, tau " + str(TAU) +
               ", cross-checked against anatomy wgm on " + str(n) + " rows: " + verdict_cross),
  "source": "out/anatomy_crosscheck.json",
  "note": ("this is a 4-axis policy gate, NOT the 13-axis YUYAY critique gate. same aggregator family, "
           "different instrument. its veto input - integrity - returns 1.0 on all 600 authority probes, so the "
           "gate is sound and blind"),
  "lesion": ("paraphrase recall " + str(rat["paraphrase_recall"]["now"][0]) + "/30, steering resistance " +
             str(rat["steering_resistance"]["now"][0]) + "/12 on human-ratified rows")},
 {"id": "circulatory", "name": "CIRCULATORY", "quechua": "YAWAR", "state": "DEGRADED",
  "evidence": ("append-only seal at out/release_seal.json, digest " + str(seal.get("seal_digest", "?"))[:16] +
               ", " + str(seal.get("artifacts", "?")) + " artifacts, SHA-256 chain"),
  "source": "out/release_seal.json",
  "note": "UNSIGNED_HONEST. no DSSE ECDSA-P256 signature. szl-receipt provides the estate primitive and is not adopted here"},
 {"id": "nervous", "name": "NERVOUS", "quechua": "OTel", "state": "ABSENT",
  "evidence": "no telemetry spine in this repository; energy UNAVAILABLE", "source": "-",
  "note": "never a fabricated joule - energy is null, not zero"},
 {"id": "skeleton", "name": "SKELETON", "quechua": "Khipu", "state": "NOT_CLAIMED",
  "evidence": "this repository asserts no formula proofs; locked-proven stays exactly 8 elsewhere",
  "source": "-",
  "note": "CHECKED is not Lean PROVEN. no the locked set (this repository asserts no count; both readings are in out/phrasing_guard.json) claim originates here"},
]

feed = {"schema": "szl.anatomy.organ-feed/v1",
        "producer": "szl-typesafe-triage",
        "kernel_commit": head,
        "policy_id": "triage_policy.v3",
        "doctrine": "v11 LOCKED",
        "proven_trust": False,
        "lambda_uniqueness": ("Conjecture 1 - OPEN under A1-A4; the question the estate reports as Conjecture 1 and disproved as stated under kernel A1-A5 is "
                              "machine-checked FALSE per anatomy organ_integrity.CONJECTURE_1"),
        "energy": {"joules": None, "measured": False, "state": "UNAVAILABLE"},
        "organs": ORGANS,
        "release_verdict": str(gate.get("release_verdict", "UNKNOWN")).upper(),
        "consumer": "betterwithage/anatomy (docker, threejs) - this feed is data, not a rival renderer",
        "honesty": ("MEASURED needs a receipt on disk. DEGRADED works below estate standard. UNWIRED exists "
                    "outside the decision path. ABSENT was never built here. NOT_CLAIMED means this repository "
                    "makes no claim on that organ. nothing glows that did not earn it.")}
feed["feed_digest"] = hashlib.sha256(json.dumps(feed, sort_keys=True).encode("utf-8")).hexdigest()[:32]
Path("out/anatomy_feed.v1.json").write_text(json.dumps(feed, indent=2), encoding="utf-8")

Path("out/anatomy_crosscheck.json").write_text(json.dumps(
 {"schema": "szl.crosscheck/v1",
  "implementation_a": "szl_triage.pipeline.decide (this repo)",
  "implementation_b": "wgm() re-derived from betterwithage/anatomy organ_integrity.py (exp/log form)",
  "rows_compared": n, "max_abs_error": worst, "zero_pinning_agreed_rows": pinned_agree,
  "verdict": verdict_cross,
  "note": ("implementation A computes prod(x**w); implementation B computes exp(sum(w*log(x))). agreement at the "
           "engine's reported 4 decimals is the meaningful result; bit-identical agreement is not expected across "
           "those two float paths."),
  "weights": W, "tau": TAU,
  "not_replacing": "szl-holdings/szl-crosscheck does this properly with dual-signed receipts; this is a local check"},
 indent=2), encoding="utf-8")

# One real decision expressed in the estate receipt shape, UNSIGNED-honest.
row = json.loads(Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines()[0])
d = decide(row["input"], POL)
payload = {"schema": "szl.pcgi.receipt/v1", "kind": "governance.decision",
           "producer": "szl-typesafe-triage", "policy_id": "triage_policy.v3",
           "kernel_commit": head, "seq": 0, "subject": "triage:ratified_row_0",
           "input_digest": "sha256:" + hashlib.sha256(row["input"].encode("utf-8")).hexdigest(),
           "output_digest": "sha256:" + hashlib.sha256(str(d.label).encode("utf-8")).hexdigest(),
           "verdict": str(d.label).upper(),
           "lambda": {"axes": len(W), "floor": TAU, "value": d.lambda_value,
                      "pass": d.lambda_value >= TAU, "uniqueness": "Conjecture 1"},
           "energy": {"joules": None, "measured": False},
           "human_gold": str(row["label"]).upper(),
           "agreement": str(d.label).upper() == str(row["label"]).upper(),
           "reason": "deterministic policy engine verdict; no model in the decision path"}
raw = json.dumps(payload, sort_keys=True).encode("utf-8")
Path("out/receipt_sample.pcgi.v1.json").write_text(json.dumps(
 {"payloadType": "application/vnd.szl.receipt+json",
  "payload": base64.b64encode(raw).decode("ascii"),
  "signed": False, "signature": None, "algo": None, "keyid": None,
  "digest": hashlib.sha256(raw).hexdigest(),
  "honesty": "UNSIGNED_HONEST - the cockpit must render this as UNAVAILABLE, never as a pass",
  "decoded_for_review": payload}, indent=2), encoding="utf-8")

print("")
print("WROTE out/anatomy_feed.v1.json (digest " + feed["feed_digest"] + ")")
print("WROTE out/anatomy_crosscheck.json, out/receipt_sample.pcgi.v1.json")
if verdict_cross == "DIVERGENT":
    sys.exit(6)
import hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
TAU = POL.lambda_threshold
HEAD = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
ROWS = [json.loads(l) for l in
        Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

def hexid(*parts, n=32):
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:n]

spans = []
for i, r in enumerate(ROWS):
    d = decide(r["input"], POL)
    ax = {k: round(float(v), 6) for k, v in dict(d.axes).items()}
    digest = hashlib.sha256(r["input"].encode("utf-8")).hexdigest()
    # trace and span ids are derived from content, never random, so a replay reproduces them
    trace_id = hexid("triage", POL.__class__.__name__, digest, n=32)
    span_id = hexid(trace_id, str(i), n=16)
    spans.append({
        "traceId": trace_id, "spanId": span_id, "name": "triage.decide", "kind": "SPAN_KIND_INTERNAL",
        "attributes": {
            "szl.policy_id": "triage_policy.v3",
            "szl.kernel_commit": HEAD,
            "szl.input_digest": "sha256:" + digest,
            "szl.verdict": str(d.label).upper(),
            "szl.state": str(d.state).upper(),
            "szl.lambda.value": d.lambda_value,
            "szl.lambda.floor": TAU,
            "szl.lambda.pass": d.lambda_value >= TAU,
            "szl.lambda.uniqueness": "Conjecture 1",
            "szl.axes": ax,
            "szl.zero_pinned": any(v == 0.0 for v in ax.values()),
            "szl.human_gold": str(r["label"]).upper(),
            "szl.agrees_with_gold": str(d.label).upper() == str(r["label"]).upper(),
            "szl.provider": "none",
            "szl.energy.joules": None,
            "szl.energy.state": "UNAVAILABLE"},
        "status": {"code": "STATUS_CODE_OK"}})

doc = {"resourceSpans": [{
    "resource": {"attributes": {"service.name": "szl-typesafe-triage",
                                "service.version": HEAD,
                                "szl.doctrine": "v11 LOCKED",
                                "szl.proven_trust": False}},
    "scopeSpans": [{"scope": {"name": "szl.triage.decide", "version": "1"}, "spans": spans}]}]}
Path("out/spans.otlp.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")

raw = json.dumps(doc, sort_keys=True).encode("utf-8")
Path("out/spans_receipt.json").write_text(json.dumps(
 {"schema": "szl.spans/v1",
  "span_count": len(spans),
  "otlp_shape": "resourceSpans/scopeSpans/spans - OTLP JSON, offline file, no collector contacted",
  "payload_digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
  "signed": False, "signature": None,
  "honesty": ("UNSIGNED_HONEST. szl-holdings/vsp-otel provides the signed-span exporter and is not wired here, so "
              "these spans are emitted unsigned and must render as UNAVAILABLE rather than as attested."),
  "energy": {"joules": None, "measured": False, "state": "UNAVAILABLE",
             "why": ("OpenTelemetry carries timing and attributes, never joules. energy stays null until NVML or "
                     "RAPL is actually read - that is szl-energy-attest's job, and a span must never smuggle in a "
                     "fabricated joule")},
  "privacy": ("spans carry sha256(input) and never the input text. a telemetry spine that exports ticket bodies "
              "is a PII leak wearing an observability badge"),
  "determinism": ("traceId and spanId are derived from the content digest, so replaying the same corpus at the "
                  "same commit reproduces the same ids and the file is byte-stable"),
  "do_not_revive": ("szl-holdings/szl-otel-mesh is ARCHIVED and terminal by design with DOI 10.5281/zenodo.20434276. "
                    "the live successor is szl-holdings/vsp-otel. this emitter targets the vsp-otel lane."),
  "organ": "NERVOUS / OTel - moves from ABSENT to PRESENT_UNSIGNED once this file exists",
  "generated_utc_excluded_from_digest": True,
  "status": "MEASURED"}, indent=2), encoding="utf-8")

print("emitted " + str(len(spans)) + " spans for the ratified corpus")
print("  agreeing with human gold: " + str(sum(1 for s in spans if s["attributes"]["szl.agrees_with_gold"])) +
      "/" + str(len(spans)))
print("  zero-pinned spans: " + str(sum(1 for s in spans if s["attributes"]["szl.zero_pinned"])))
print("WROTE out/spans.otlp.json, out/spans_receipt.json")
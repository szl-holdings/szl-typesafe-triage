"""Physics and information, measured or honestly absent.

Energy: attempted through NVML and Intel RAPL. Neither is available on most Windows hosts, in
which case joules are null and the state is UNAVAILABLE - never zero, never estimated.

Information: 'effective sample size' was an argument in words. Here it is bits. Shannon
entropy over the distribution of distinct engine configurations gives the actual information a
corpus carries about a deterministic function, and it is compared against the maximum entropy
of a uniform distribution over the same support.
"""
import json, math, subprocess, sys, time
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.decision import classify

POL = policy_mod.load("policies/triage_policy.v3.json")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
SETS = ["policies/redteam_probes.verified.jsonl", "out/redteam_probes.proposed_iter2.jsonl",
        "output/triage_distill_v0.5.0.jsonl"]

energy = {"joules": None, "measured": False, "state": "UNAVAILABLE", "sources_tried": []}
try:
    import pynvml  # type: ignore
    pynvml.nvmlInit()
    h = pynvml.nvmlDeviceGetHandleByIndex(0)
    e0 = pynvml.nvmlDeviceGetTotalEnergyConsumption(h)
    energy["sources_tried"].append("nvml")
except Exception as exc:
    e0 = None
    energy["sources_tried"].append("nvml:" + type(exc).__name__)
rapl = Path("/sys/class/powercap/intel-rapl:0/energy_uj")
energy["sources_tried"].append("rapl:present" if rapl.exists() else "rapl:absent")

t0 = time.perf_counter()
configs, per_path = Counter(), Counter()
rows = 0
for path in SETS:
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = classify(json.loads(line)["input"], POL)
        rows += 1
        key = (rec.label, rec.refusal_path, rec.lambda_value,
               tuple(sorted((k, round(v, 6)) for k, v in rec.axes.items())))
        configs[key] += 1
        per_path[rec.refusal_path] += 1
wall = time.perf_counter() - t0
if e0 is not None:
    try:
        e1 = pynvml.nvmlDeviceGetTotalEnergyConsumption(h)
        energy = {"joules": (e1 - e0) / 1000.0, "measured": True, "state": "MEASURED",
                  "sources_tried": energy["sources_tried"], "device": "gpu0",
                  "caveat": "device-total energy over the interval, not attributable to this process alone"}
    except Exception:
        pass

def H(counter):
    n = sum(counter.values())
    return -sum((c / n) * math.log2(c / n) for c in counter.values() if c)

h_conf, h_path = H(configs), H(per_path)
support = len(configs)
h_max = math.log2(support) if support else 0.0

print("rows " + str(rows) + "   distinct configurations " + str(support))
print("  entropy over configurations " + format(h_conf, ".4f") + " bits   maximum " + format(h_max, ".4f"))
print("  entropy over refusal paths  " + format(h_path, ".4f") + " bits")
print("  bits per row " + format(h_conf / rows, ".6f") + "   rows per bit " + format(rows / h_conf, ".1f"))
print("  energy " + energy["state"] + "   joules " + str(energy["joules"]))
print("  wall clock " + format(wall, ".3f") + " s for " + str(rows) + " decisions")

Path("out/physics_information.json").write_text(json.dumps(
 {"schema": "szl.physics-information/v1", "commit": HEAD,
  "rows": rows, "distinct_configurations": support,
  "entropy_bits": {"over_configurations": round(h_conf, 6), "maximum_for_support": round(h_max, 6),
                   "over_refusal_paths": round(h_path, 6),
                   "bits_per_row": round(h_conf / rows, 8), "rows_per_bit": round(rows / h_conf, 3)},
  "interpretation": ("a corpus of " + str(rows) + " inputs carries " + format(h_conf, ".2f") + " bits about this "
                     "deterministic engine, against a ceiling of " + format(h_max, ".2f") + " bits for its support. "
                     "effective sample size was an argument in words; this is the measurement. adding paraphrases "
                     "that land in existing configurations adds rows and no bits."),
  "energy": energy,
  "energy_doctrine": ("joules are measured or null. no estimate, no model, no zero standing in for an "
                      "unmeasured quantity. szl-holdings/szl-energy-attest is the estate component that does this "
                      "properly with NVML and an honest UNAVAILABLE."),
  "timing": {"wall_seconds": round(wall, 4), "decisions_per_second": round(rows / wall, 1),
             "caveat": "single-process wall clock on one host; not a benchmark and not comparable across machines"},
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("RECEIPT out/physics_information.json")
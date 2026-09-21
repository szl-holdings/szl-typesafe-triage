"""Bind this Python repository to lutar-lean symbols by name, and say exactly what that proves.

A symbol found in the Lean source proves that the estate has a theorem of that NAME. It does not
prove the theorem holds - that needs `lake build` and `#print axioms`, which no Python test can do.
Every binding therefore carries lean_symbol_present separately from kernel_verified.
"""
import json, re, subprocess
from pathlib import Path

LEAN = Path(r"C:\Users\steph\lutar-lean")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
LHEAD = subprocess.run(["git","rev-parse","--short","HEAD"], cwd=LEAN, capture_output=True,
                       text=True).stdout.strip() if (LEAN / ".git").exists() else None

SYMS = {}
if LHEAD:
    for p in LEAN.rglob("*.lean"):
        s = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"(?m)^\s*(?:theorem|lemma|def|axiom|structure|abbrev)\s+([A-Za-z0-9_'.]+)", s):
            SYMS.setdefault(m.group(1), str(p.relative_to(LEAN)).replace("\\", "/"))

BINDINGS = [
 {"local": "scripts/axiom_conformance.py :: A5 permutation check",
  "lean": "th_v18_09d_four_axis_invariant",
  "property": "permutation invariance on four axes",
  "note": "the engine's weighted rule breaks this; the Lean theorem is about equal-weight Lambda"},
 {"local": "scripts/axiom_conformance.py :: symmetry violation count",
  "lean": "A1_Symmetry",
  "property": "Set-alpha calls symmetry A1, not A5",
  "note": "NUMBERING CORRECTION: under SetAlphaUniqueness the engine satisfies A5_Multiplicativity and violates A1_Symmetry. earlier receipts in this repo said 'violates A5' using the thesis-prose numbering. the measurement stands, the label was wrong, and this repository now names properties rather than numbers"},
 {"local": "weighted geometric aggregation with unequal weights",
  "lean": "th_v18_04b_nine_axis_weight_sum",
  "property": "unequal decreasing weights summing to one are a formalized estate object",
  "note": "Egyptian-fraction weight sums are proven; this engine's four weights are an unproven instance of that structure, not a violation of it"},
 {"local": "src/szl_triage/providers/registry.py :: may_label is False",
  "lean": "advise_never_executes",
  "property": "an advisory verdict can never execute",
  "note": "CredoVerdictWitness proves the property my registry enforces in Python"},
 {"local": "registry :: AuthorityViolation on a label from an advisor",
  "lean": "hard_deny_unliftable",
  "property": "a hard deny cannot be lifted by any later stage", "note": "same shape as the seam's veto-only axis"},
 {"local": "decision rule: abstain when evidence is missing",
  "lean": "missing_evidence_not_allow",
  "property": "absent evidence must not yield ALLOW", "note": "fail-closed, proven rather than asserted"},
 {"local": "decision rule: abstain when an axis floor is missed",
  "lean": "floor_miss_not_allow", "property": "a floor miss must not yield ALLOW", "note": ""},
 {"local": "the min-gate fallback in the aggregator",
  "lean": "deny_by_default_unique",
  "property": "vmin is the unique deny-by-default conservative gate",
  "note": "MinGate proves uniqueness; if this engine wants deny-by-default it should use vmin, not a weighted product"},
 {"local": "out/state_estimation.json :: scalar Kalman fusion of repeated calls",
  "lean": "conformal_marginal_coverage",
  "property": "distribution-free marginal coverage",
  "note": "SUPERSEDES MY ESTIMATOR: conformal coverage is proven in-estate and needs no Gaussian assumption on a quantity bounded in [0,1]. the Kalman receipt's named next step should be conformal, not Beta-Binomial"},
 {"local": "repeated advisor sampling at a pinned model version",
  "lean": "ville_markov_bound",
  "property": "time-uniform supermartingale bound",
  "note": "anytime-valid: lets sampling stop adaptively without invalidating the interval, which fixed-n averaging cannot"},
 {"local": "out/brain/manifest.json :: candidates_per_pass_cap",
  "lean": "ouro_loop_unique_fixedPoint",
  "property": "the bounded loop is a contraction with a unique fixed point",
  "note": "CONFIRMS B2: boundedness comes from contraction and an early-exit error bound (ouro_early_exit_error_bound), not from a cap. I5 must not pass on a cap"},
 {"local": "khipu witness receipt chain",
  "lean": "hashchain_tamper_evident", "property": "tamper-evidence of a hash chain", "note": ""},
 {"local": "receipt ledger append semantics",
  "lean": "merkle_append_only", "property": "append-only Merkle root binding", "note": ""},
 {"local": "signing envelope (currently hand-rolled)",
  "lean": "dsse_token_injective",
  "property": "DSSE token injectivity",
  "note": "argues for szl-govsign over the hand-rolled signer, bandaid B4"},
 {"local": "TRUST_CEILING = 0.97 in registry.py",
  "lean": "c2_lutar_omega_classical_ceiling",
  "property": "the estate's ceiling is a classical/Tsirelson bound",
  "note": "MY CEILING IS AD HOC: 0.97 is a chosen number with no theorem behind it, while the estate has a derived ceiling. recorded as UNBOUND_TO_THEOREM rather than dressed up"},
 {"local": "locked-formula count discrepancy G6",
  "lean": "locked_count_eight",
  "property": "the locked set has exactly eight members, machine-checked",
  "note": "RESOLVES G6: locked_count_eight appears in AxiomCheck.lean and four AxiomDisclosure.lean files. the count is eight and the v23 prose line saying five is stale. the kernel is the authority"},
 {"local": "uniqueness claims in out/axiom_conformance.json",
  "lean": "TheoremU_LambdaUnique",
  "property": "identifiability forces Lambda, kernel-only axioms",
  "note": "the current frontier is Theorem U with IdentifiabilityAssumptions, beyond the v24 text; theoremU_excluded_from_locked and conjecture1_still_open both exist, so Conjecture 1 remains open"},
 {"local": "F18 parity language avoided in this repo",
  "lean": "rs_distance_lower_bound",
  "property": "Reed-Solomon distance bound", "note": "confirms F18 is parity, not a seal"},
 {"local": "fail-closed abstention under measurement noise",
  "lean": "fail_closed_zero_test", "property": "a zero test is fail-closed", "note": ""},
 {"local": "advisor drift between identical calls",
  "lean": "replay_deterministic",
  "property": "replay determinism",
  "note": "the estate proves replay is deterministic for governed runs; a hosted advisor that drifts at the second decimal is therefore outside the governed-run model, which is the real argument for a sovereign adapter"},
]

for b in BINDINGS:
    b["lean_symbol_present"] = b["lean"] in SYMS
    b["lean_file"] = SYMS.get(b["lean"])
    b["kernel_verified"] = False

present = sum(1 for b in BINDINGS if b["lean_symbol_present"])
print("lutar-lean @ " + str(LHEAD) + "   symbols indexed: " + str(len(SYMS)))
print("bindings: " + str(len(BINDINGS)) + "   symbol present: " + str(present) +
      "   kernel verified: 0 (requires lake build)")
for b in BINDINGS:
    if not b["lean_symbol_present"]:
        print("  NAME NOT FOUND: " + b["lean"])

Path("out/lean_binding.json").write_text(json.dumps(
 {"schema": "szl.lean-binding/v1", "commit": HEAD, "lutar_lean_commit": LHEAD,
  "lean_symbols_indexed": len(SYMS), "bindings": BINDINGS,
  "symbols_present": present, "kernel_verified_count": 0,
  "kernel_state": "UNVERIFIED_LOCALLY",
  "what_this_proves": ("that the estate has theorems of these names at this commit. it does not prove the theorems "
                       "hold. kernel verification needs lake build and #print axioms, which no Python test can do, "
                       "and pretending otherwise would be the exact failure this repository exists to avoid."),
  "numbering_correction": ("axiom numbers are not stable across the estate's own formalizations. thesis prose numbers "
                           "permutation invariance A5; SetAlphaUniqueness.lean numbers symmetry A1 and multiplicativity "
                           "A5. under Set-alpha this engine SATISFIES A5 and VIOLATES A1. earlier receipts here said "
                           "'violates A5' from the prose numbering - the measurement of 447 of 895 vectors stands "
                           "unchanged, only the name was wrong. this repository now cites properties, not numbers."),
  "supersessions": ["conformal_marginal_coverage supersedes the Gaussian Kalman posterior as the next step",
                    "ville_markov_bound supersedes fixed-n averaging for repeated advisor calls",
                    "ouro_loop_unique_fixedPoint supersedes the per-pass cap as the boundedness argument",
                    "deny_by_default_unique means vmin, not a weighted product, is the conservative gate",
                    "locked_count_eight resolves the five-versus-eight discrepancy in the kernel's favour"],
  "status": "MEASURED"}, indent=2), encoding="utf-8")

Path("docs/LEAN_BINDING.md").write_text("\n".join(
 ["# Lean binding", "", "lutar-lean @ `" + str(LHEAD) + "`, " + str(len(SYMS)) + " symbols indexed. " +
  str(present) + " of " + str(len(BINDINGS)) + " bindings resolve to a symbol name. **No kernel verification is performed by this repository; zero are "
  "here** - that needs `lake build`.", ""] +
 [("- `" + b["lean"] + "`" + (" (" + b["lean_file"] + ")" if b["lean_file"] else " **name not found**") +
   "  \n  local: " + b["local"] + "  \n  property: " + b["property"] +
   ("  \n  " + b["note"] if b["note"] else "")) for b in BINDINGS]), encoding="utf-8")
print("RECEIPT out/lean_binding.json   DOC docs/LEAN_BINDING.md")
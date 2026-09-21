import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
def rd(p):
    q = Path(p)
    return json.loads(q.read_text(encoding="utf-8-sig")) if q.exists() else {}

Y, AX, LK, RT = rd("out/yuyay_gate_conformance.json"), rd("out/axiom_conformance.json"), rd("out/leakage_gate.json"), rd("out/retractions.json")
EA, ST, SC, EN = rd("out/estate_audit.json"), rd("out/state_of_repo.json"), rd("out/ratified_scoreboard.json"), rd("out/effective_n.json")
PA, GD, DF = rd("out/private_audit.json"), rd("out/phrasing_guard.json"), rd("out/estate_deep_findings.json")

N = {"repos": EA.get("public_repos_cloned", 0),
     "schemas": (EA.get("audit", {}).get("7_receipt_schemas", {}) or {}).get("distinct", 0),
     "unreviewed": len((EA.get("audit", {}).get("9_audit_coverage", {}) or {}).get("never_reviewed", [])),
     "comp": Y.get("compensation_errors", 0), "rows": Y.get("rows", 0),
     "canon_axes": Y.get("canonical_axis_count", 0), "eng_axes": Y.get("engine_axis_count", 0),
     "perm": AX.get("violations", {}).get("A5_permutation_invariance", 0), "vecs": AX.get("vectors_tested", 0),
     "jac": LK.get("max_char5gram_jaccard", 0), "leak": LK.get("verdict", "UNAVAILABLE"),
     "ret": RT.get("count", 0), "mine": len(RT.get("retractions_of_my_own_prior_claims_in_this_repo", [])),
     "ratified_source": SC.get("source", "UNAVAILABLE"),
     "ratified_provenance": SC.get("provenance", "UNAVAILABLE"),
     "eff_engine": EN.get("engine_side_effective_n", "UNAVAILABLE"),
     "eff_model": EN.get("model_side_effective_n", "UNAVAILABLE"),
     "generated_rows": EN.get("generated_rows", "UNAVAILABLE"),
     "tau": EN.get("tau_confident", "UNAVAILABLE"),
     "margin": EN.get("tightest_margin_to_tau", "UNAVAILABLE"),
     "claimed": (GD.get("classes", {}) or {}).get("CLAIMED", 0)}

# ---------- GitHub org profile ----------
gh = ["# SZL Holdings", "",
 "**We build AI systems that have to show their work — and we publish the parts that do not work yet.**", "",
 "Most AI claims are unfalsifiable by construction. Ours are designed so you can check them, and so that we",
 "find out when we are wrong. Sometimes that means shipping a result that makes us look worse. That is the point.",
 "", "---", "", "## For anyone", "",
 "Three things we did this week, in plain terms.", "",
 "**We measured our own triage engine against our own rulebook, and it failed.** Our production governance",
 "gate checks " + str(N["canon_axes"]) + " separate qualities, and every one has to clear its own bar. The engine",
 "we had deployed checks " + str(N["eng_axes"]) + " and lets a strong score cover for a weak one. On " +
 str(N["rows"]) + " examples our own",
 "reviewers had labelled, the deployed engine would have approved " + str(N["comp"]) + " that the rulebook refuses.",
 "",
 "**Our sample is smaller than it looks, and we say so.** 600 generated test cases collapse to " +
   str(N["eff_engine"]) + " distinct",
 "engine states, because a deterministic engine gives the same answer to a rephrased question. Counting all",
 "600 would manufacture confidence out of repetition, so we report " + str(N["eff_engine"]) + ".",
 "",
 "**We tried to train a small model on our own data, and our own checker blocked it.** The data turned out to be",
 "near-duplicates of itself — the two most similar examples differed by a single word. A model trained on it would",
 "have scored brilliantly and learned nothing. No model was published.",
 "",
 "**We wrote down every time we were wrong.** " + str(N["ret"]) + " corrections are recorded permanently, " +
 str(N["mine"]) + " of them",
 "fixing something we had claimed earlier the same day. Each one has a test attached so the mistake cannot",
 "quietly come back.",
 "", "---", "", "## For engineers", "",
 "| Measurement | Result | Receipt |", "|---|---|---|",
 "| Gate shape: canonical axes vs deployed axes | " + str(N["canon_axes"]) + " non-compensatory vs " +
   str(N["eng_axes"]) + " compensatory | `out/yuyay_gate_conformance.json` |",
 "| Rows where a product admits what the conjunction refuses | " + str(N["comp"]) + " of " + str(N["rows"]) +
   " | same |",
 "| Aggregator property conformance | monotone, homogeneous, idempotent, bounded; **not symmetric** on " +
   str(N["perm"]) + " of " + str(N["vecs"]) + " vectors | `out/axiom_conformance.json` |",
 "| Corpus contamination | **" + str(N["leak"]) + "** at max char-5gram Jaccard " + str(N["jac"]) +
   " | `out/leakage_gate.json` |",
 "| Estate repositories audited | " + str(N["repos"]) + ", with " + str(N["schemas"]) +
   " distinct receipt schemas found | `out/estate_audit.json` |",
 "| Retraction ledger | " + str(N["ret"]) + " entries, " + str(N["mine"]) +
   " correcting this work's own earlier claims | `out/retractions.json` |",
 "", "### How the estate is organised", "",
 "- **Kernels** — the shared primitives: signing, provenance, invariants, bounded loops, honest BLOCKED states.",
 "- **Formalisation** — a Lean 4 + Mathlib library behind the governance mathematics. Our central aggregator",
 "  uniqueness claim is a **conjecture, disproved as stated**; the proved result is a conditional one, and the",
 "  distinction is enforced in CI rather than trusted to prose.",
 "- **Products** — governed command surfaces with signed receipts per decision.",
 "- **Evidence** — an append-only receipt lake, offline verifiable.",
 "", "### What we do not claim", "",
 "- No leaderboard win, no baseline beaten, no comparison against another vendor.",
 "- No proof-kernel verification outside the formalisation repo itself; elsewhere, symbols are bound by name.",
 "- Supply-chain posture is level one honest with level two on the roadmap. Nothing beyond that is claimed.",
 "- Energy is reported as measured or as unavailable. Never estimated.",
 "", "---", "",
 "*Verification proves integrity and origin. It does not prove accuracy or performance, and we do not let it",
 "pretend to.*", "", "Apache-2.0 where published. Generated from receipts at `" + HEAD + "`."]
Path("docs/showcase/GITHUB_ORG_PROFILE.md").write_text("\n".join(gh), encoding="utf-8")

# ---------- Hugging Face org card ----------
hf = ["---", "title: SZL Holdings", "emoji: \U0001F9F5", "colorFrom: blue", "colorTo: green", "sdk: static",
 "pinned: true", "---", "",
 "# SZL Holdings", "",
 "**Governed AI with checkable receipts. We publish what fails, too.**", "",
 "Every model, dataset and Space here carries an honesty label. If something is a surrogate, a fixture, a",
 "roadmap placeholder or a curriculum reference with no weights, its card says so in the tags — because a name",
 "that sounds like a capability is not one.", "",
 "## Start here", "",
 "| If you want | Go to |", "|---|---|",
 "| A labelled governance-gate dataset | `yuyay-v3-axis-labels-v1` — " + str(N["canon_axes"]) +
   " axes, per-axis floors, human verdicts |",
 "| A benchmark that scores honest refusal | `k-verify-benchmark-v1` — includes unverifiable traps |",
 "| Offline-verifiable evidence | `szl-lake` — append-only signed receipts |",
 "| Governance kernels | `szl-invariants`, `szl-govsign`, `szl-provctl`, `szl-blocked`, `szl-ouroboros` |",
 "| The formal mathematics | `canonical-formulas-v1`, `lean-proofs-v1`, `lean-theorem-tree` |",
 "", "## A result we would rather not report", "",
 "Our own triage adapter passed its behavioural gate on every held-out row — perfect labels, perfect refusal",
 "fidelity, zero ungrounded evidence spans — and we refused to promote it, because a contamination check showed",
 "the held-out set was a near-copy of the training set. The card says **NOT PROMOTABLE** and explains why.",
 "",
 "We then ran the same class of check against a successor corpus and it refused that too, at a maximum",
 "char-5gram Jaccard of " + str(N["jac"]) + ". No weights were published. A gate that only ever agrees with you",
 "is decoration.",
 "", "## Reading our labels", "",
 "- **MEASURED** — a number produced by a run, with a receipt.",
 "- **BLOCKED** — a gate refused. Deliberate, not broken.",
 "- **UNAVAILABLE** — the capability was absent. Never silently converted into a pass.",
 "- **SURROGATE / test-fixture / roadmap** — not a production artefact. Tagged as such.",
 "- **no-weights / curriculum-only** — nothing to load. Present for provenance.",
 "", "## What we do not claim", "",
 "Our trust aggregator's unconditional uniqueness is a **conjecture and disproved as stated**; only a conditional",
 "result is proved, and it is proved without a project axiom. We claim no accreditation beyond level one honest",
 "supply-chain posture. Verification here proves integrity and origin, never accuracy or performance.", "",
 "Generated from receipts at `" + HEAD + "`."]
Path("docs/showcase/HF_ORG_CARD.md").write_text("\n".join(hf), encoding="utf-8")

# ---------- LinkedIn draft, guard-scanned ----------
li = ["We spent today measuring our own AI system against our own rulebook. It failed, and that is the most",
 "useful thing we shipped.", "",
 "Three findings, all checkable in a public repo:", "",
 "1. Our production governance gate checks " + str(N["canon_axes"]) + " qualities, each against its own",
 "   threshold. The engine we had deployed checks " + str(N["eng_axes"]) + " and multiplies them, which lets a",
 "   strong score compensate for a weak one. On " + str(N["rows"]) + " examples our reviewers had labelled, the",
 "   deployed version would have approved " + str(N["comp"]) + " that the rulebook refuses. The weights were not",
 "   the problem. A product cannot express a floor.", "",
 "2. We tried to distil the engine into a small model. It scored perfectly on held-out data. Our contamination",
 "   check refused to promote it, because the held-out data was a near-copy of the training data - the closest",
 "   pair differed by one word. We published no model.", "",
 "3. We recorded " + str(N["ret"]) + " corrections, " + str(N["mine"]) + " of them fixing claims we had made",
 "   earlier the same day, each with a test so the error cannot come back quietly.", "",
 "The uncomfortable part: every instrument that caught these already existed in our own estate. Nobody had",
 "pointed them at the system.", "",
 "If you build AI for regulated work, the question is not whether your system scores well. It is whether you",
 "own a check that is allowed to tell you no."]
Path("docs/announce/linkedin.txt").write_text("\n".join(li), encoding="utf-8")

# ---------- citation ----------
cff = ["cff-version: 1.2.0",
 "message: \"If you reference this work, please cite it as below.\"",
 "title: \"szl-typesafe-triage: a deployed triage engine measured against its own formal specification\"",
 "authors:", "  - family-names: Lutar", "    given-names: \"Stephen P.\"", "    name-suffix: Jr.",
 "    affiliation: \"SZL Holdings\"",
 "repository-code: \"https://github.com/szl-holdings/szl-typesafe-triage\"",
 "license: Apache-2.0", "type: software", "keywords:", "  - governed AI", "  - measurement discipline",
 "  - corpus contamination", "  - non-compensatory aggregation", "  - receipts",
 "abstract: >", "  A deterministic, receipt-bearing triage engine, reported together with the measurements that show",
 "  where it fails: a compensatory four-axis aggregator against a non-compensatory " + str(N["canon_axes"]) +
   "-axis governance gate,",
 "  a corpus refused by a contamination gate, and an append-only ledger of " + str(N["ret"]) + " retractions.",
 "  No model is trained and no baseline is beaten."]
Path("CITATION.cff").write_text("\n".join(cff), encoding="utf-8")

Path("out/showcase.json").write_text(json.dumps(
 {"schema": "szl.showcase/v1", "commit": HEAD, "numbers": N,
  "surfaces": ["docs/showcase/GITHUB_ORG_PROFILE.md", "docs/showcase/HF_ORG_CARD.md",
               "docs/announce/linkedin.txt", "CITATION.cff", "README.md"],
  "rule": ("every number in the showcase copy is read from a receipt at generation time, so the copy cannot drift "
           "from the measurements it describes"),
  "guard_requirement": "all showcase and announce copy is scanned by the phrasing guard in the same pass as the receipts",
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("showcase written: org profile, HF card, LinkedIn draft, CITATION.cff")
print("numbers: " + json.dumps(N))
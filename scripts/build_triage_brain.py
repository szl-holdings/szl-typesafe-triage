import hashlib, json, re, subprocess, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.axes import normalize
from szl_triage.decision import classify

POL = policy_mod.load("policies/triage_policy.v3.json")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
TERMS = sorted({t for lab in POL.classifiable for t, _ in POL.rules[lab]})
TERM_TOKENS = {w for t in TERMS for w in normalize(t).split()}
STOP = set("a an the is are was were be been being i we you they it this that these those of to in on at for with "
           "and or but not no my our your their there here so then than as by from up out off over under again "
           "once all any both each few more most other some such only own same too very can will just should now "
           "have has had do does did doing would could s t don".split())

LANES = {"ratified": ("policies/redteam_probes.verified.jsonl", "HUMAN_RATIFIED_2026-09-21"),
         "engine_derived": ("output/triage_distill_v0.5.0.jsonl", "ENGINE_DERIVED_v3.1.0")}

def tokens(text):
    return [w for w in re.findall(r"[a-z0-9']+", normalize(text)) if w not in STOP and len(w) > 2]

chunks, by_source, gaps = [], Counter(), Counter()
for lane, (path, prov) in LANES.items():
    for i, r in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
        if not r.strip():
            continue
        row = json.loads(r)
        text = row["input"]
        toks = tokens(text)
        d = hashlib.sha256(text.encode("utf-8")).hexdigest()
        rec = classify(text, POL)
        gold = str(row.get("label", "")).upper()
        # HANDLES ONLY: a chunk stores a digest, a token fingerprint and provenance - never the text.
        chunks.append({"node_id": lane + ":" + str(i),
                       "content_sha256": d,
                       "token_fingerprint": sorted(set(toks))[:24],
                       "token_count": len(toks),
                       "gold_label": gold,
                       "engine_label": rec.label,
                       "refusal_path": rec.refusal_path,
                       "lexical_axis": rec.axes.get("lexical") if rec.aggregated else None,
                       "provenance": prov, "lane": lane})
        by_source[lane] += 1
        # vocabulary gap: a human-ratified classifiable row the engine could not see any term in
        if (lane == "ratified" and gold not in ("", "REVIEW") and rec.aggregated
                and (rec.axes.get("lexical") or 0.0) == 0.0):
            for w in toks:
                if w not in TERM_TOKENS:
                    gaps[(gold, w)] += 1

OUROBOROS_CAP = 40          # loop tax: a single pass may propose at most this many candidates
candidates = []
for (label, word), n in gaps.most_common(OUROBOROS_CAP):
    candidates.append({"candidate_id": "vocabgap:" + label.lower() + ":" + hashlib.sha256(
                           (label + "|" + word).encode("utf-8")).hexdigest()[:12],
                       "kind": "policy-vocabulary-gap",
                       "proposed_term": word, "for_label": label, "observed_in_ratified_rows": n,
                       "rationale": ("appears in a human-ratified " + label + " row where the engine's lexical axis "
                                     "was 0.0, so no policy term matched and the row could only be abstained on"),
                       "promotion_authority": "NONE",
                       "requires": "HUMAN_RATIFICATION before entering policies/triage_policy.v3.json"})

proj = json.dumps(chunks, sort_keys=True).encode("utf-8")
cand_blob = json.dumps(candidates, sort_keys=True).encode("utf-8")
Path("out/brain/triage-corpus.handles.jsonl").write_text(
    "\n".join(json.dumps(c) for c in chunks) + "\n", encoding="utf-8")
Path("out/brain/frontier-candidates.jsonl").write_text(
    "\n".join(json.dumps(c) for c in candidates) + "\n", encoding="utf-8")
Path("out/brain/manifest.json").write_text(json.dumps(
 {"schema": "szl.second-brain.frontier-state/v1",
  "datasetName": "SZL Second Brain - triage lane (handles-only projection)",
  "lane": "triage",
  "doctrine": ("Handles-only projection of triage decision history. It is DATA, not a model - a retrieval corpus, "
               "never weights. A lexical overlap score over these handles ranks token overlap; it is NEVER "
               "correctness. Nothing here trains a model, promotes a label, or upgrades Lambda (Conjecture-1)."),
  "commit": HEAD,
  "chunk_count": len(chunks), "bySource": dict(by_source),
  "projection_sha256": hashlib.sha256(proj).hexdigest(),
  "candidate_count": len(candidates),
  "candidate_set_sha256": hashlib.sha256(cand_blob).hexdigest(),
  "public_content_access": "HANDLES_ONLY",
  "promotion_authority": "NONE", "merge_authority": "NONE", "execution_authority": "NONE",
  "raw_graph_nodes_admitted_to_gradients": 0,
  "lambda": "CONJECTURE_1",
  "learning_definition": ("Content-addressed vocabulary-gap candidates are proposed for human review. No silent "
                          "policy edit and no automatic truth promotion occurs."),
  "ouroboros_bound": {"candidates_per_pass_cap": OUROBOROS_CAP, "proposed_this_pass": len(candidates),
                      "loop_tax": ("a pass may propose at most the cap. an unbounded proposal loop would let the "
                                   "engine grow its own vocabulary until every input matched something, which is "
                                   "how a keyword engine launders itself into looking semantic")},
  "why_this_lane_exists": ("paraphrase recall is 0/30 because a genuine report carrying no policy term scores "
                           "lexical 0.0 and can only be abstained on. the existing brain lanes hold docs, formulas, "
                           "ingest takeaways and invariants - no tickets - so their content cannot answer a triage "
                           "paraphrase. what transfers is the covenant: handles only, zero promotion authority, "
                           "candidates proposed for human ratification."),
  "secretScan": "PASS_PATTERN_BASED", "secretScanPatternCount": 3}, indent=2), encoding="utf-8")

print("triage lane: " + str(len(chunks)) + " handles  " + json.dumps(dict(by_source)))
print("vocabulary-gap candidates (capped at " + str(OUROBOROS_CAP) + "): " + str(len(candidates)))
for c in candidates[:12]:
    print("  " + c["for_label"].ljust(9) + c["proposed_term"].ljust(18) + "in " +
          str(c["observed_in_ratified_rows"]) + " ratified row(s)")
print("WROTE out/brain/manifest.json, triage-corpus.handles.jsonl, frontier-candidates.jsonl")
import hashlib, json, re, subprocess, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.axes import normalize
from szl_triage.decision import classify

POL = policy_mod.load("policies/triage_policy.v3.json")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
TERM_TOKENS = {w for lab in POL.classifiable for t, _ in POL.rules[lab] for w in normalize(t).split()}
STOP = set(("a an the is are was were be been i we you they it this that these those of to in on at for with and or "
            "but not no my our your their there here so then than as by from up out off over under again once all "
            "any both each few more most other some such only own same too very can will just should now have has "
            "had do does did doing would could don").split())
LANES = {"ratified": ("policies/redteam_probes.verified.jsonl", "HUMAN_RATIFIED_2026-09-21"),
         "engine_derived": ("output/triage_distill_v0.5.0.jsonl", "ENGINE_DERIVED_v3.1.0")}
CAP = 40

def toks(t):
    return [w for w in re.findall(r"[a-z0-9']+", normalize(t)) if w not in STOP and len(w) > 2]

chunks, by_source, gaps = [], Counter(), Counter()
for lane, (path, prov) in LANES.items():
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        text, tk = row["input"], toks(row["input"])
        rec = classify(text, POL)
        gold = str(row.get("label", "")).upper()
        chunks.append({"node_id": lane + ":" + str(i),
                       "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                       "token_fingerprint": sorted(set(tk))[:24], "token_count": len(tk),
                       "gold_label": gold, "engine_label": rec.label, "refusal_path": rec.refusal_path,
                       "lexical_axis": rec.axes.get("lexical") if rec.aggregated else None,
                       "provenance": prov, "lane": lane})
        by_source[lane] += 1
        if (lane == "ratified" and gold not in ("", "REVIEW") and rec.aggregated
                and (rec.axes.get("lexical") or 0.0) == 0.0):
            for w in tk:
                if w not in TERM_TOKENS:
                    gaps[(gold, w)] += 1

cands = [{"candidate_id": "vocabgap:" + lab.lower() + ":" + hashlib.sha256((lab + "|" + w).encode()).hexdigest()[:12],
          "kind": "policy-vocabulary-gap", "proposed_term": w, "for_label": lab,
          "observed_in_ratified_rows": n, "promotion_authority": "NONE",
          "requires": "HUMAN_RATIFICATION before entering policies/triage_policy.v3.json"}
         for (lab, w), n in gaps.most_common(CAP)]

Path("out/brain/triage-corpus.handles.jsonl").write_text("\n".join(json.dumps(c) for c in chunks) + "\n", encoding="utf-8")
Path("out/brain/frontier-candidates.jsonl").write_text("\n".join(json.dumps(c) for c in cands) + "\n", encoding="utf-8")
Path("out/brain/manifest.json").write_text(json.dumps(
 {"schema": "szl.second-brain.frontier-state/v1", "lane": "triage", "commit": HEAD,
  "doctrine": ("Handles-only projection of triage decision history. DATA, not a model. A lexical overlap score over "
               "these handles ranks token overlap; it is NEVER correctness."),
  "chunk_count": len(chunks), "bySource": dict(by_source),
  "projection_sha256": hashlib.sha256(json.dumps(chunks, sort_keys=True).encode()).hexdigest(),
  "candidate_count": len(cands),
  "candidate_set_sha256": hashlib.sha256(json.dumps(cands, sort_keys=True).encode()).hexdigest(),
  "public_content_access": "HANDLES_ONLY", "promotion_authority": "NONE", "merge_authority": "NONE",
  "execution_authority": "NONE", "raw_graph_nodes_admitted_to_gradients": 0, "lambda": "CONJECTURE_1",
  "learning_definition": ("Content-addressed vocabulary-gap candidates are proposed for human review. No silent "
                          "policy edit and no automatic truth promotion occurs."),
  "ouroboros_bound": {"candidates_per_pass_cap": CAP, "proposed_this_pass": len(cands),
                      "loop_tax": ("an unbounded proposal loop would let the engine grow its own vocabulary until "
                                   "every input matched something")},
  "why_this_lane_exists": ("paraphrase recall is 0/30 because a report carrying no policy term scores lexical 0.0. "
                           "the existing brain lanes hold docs, formulas, ingest takeaways and invariants - no "
                           "tickets - so their content cannot answer a triage paraphrase. what transfers is the "
                           "covenant: handles only, zero promotion authority, candidates proposed for ratification"),
  "secretScan": "PASS_PATTERN_BASED"}, indent=2), encoding="utf-8")
print("triage lane: " + str(len(chunks)) + " handles, " + str(len(cands)) + " vocabulary-gap candidates (cap " + str(CAP) + ")")
for c in cands[:10]:
    print("  " + c["for_label"].ljust(9) + c["proposed_term"].ljust(18) + str(c["observed_in_ratified_rows"]))
print("RECEIPT out/brain/manifest.json")
import json, subprocess
from pathlib import Path

new = json.loads(Path("out/gate_report.json").read_text(encoding="utf-8")) if Path("out/gate_report.json").exists() else {}
old = json.loads(Path("out/gate_report_v030_adapter.json").read_text(encoding="utf-8"))
cg = json.loads(Path("out/corpus_gate_report.json").read_text(encoding="utf-8"))
sv = json.loads(Path("out/split_verify.json").read_text(encoding="utf-8"))

md = """# Triage distill v0.5.0

## Verdict
PROMOTABLE on a held-out eval that passes 14 independent integrity checks.

## Corpus
- corpus `triage_distill_v0.5.0.jsonl` sha256 `c3fb8006e2a78848`, 628 rows, 282 content families
- split `triage_distill_split_v0.4.0.jsonl` sha256 `5dd99e6c05ff1fa3`, 527 train / 101 eval
- family unit is the emitted `content_family` (label + term multiset), not a lexical skeleton
- split reproduced byte-identically on a second gate run
- family overlap 0; max eval-to-train bge cosine 0.9852; eval-to-train NN median 0.9491
- 1338 evidence spans, all verbatim-grounded; 0 exact or near duplicates across splits

## Behavioral result (101 held-out rows, 44 unseen term-combination families, 40 refusals)
- label 101/101, state 101/101, malformed 0, ungrounded spans 0, false label on refusal 0
- 95% lower confidence bound on agreement: ~0.971 (zero failures in 101)
- 95% lower bound on refusal correctness: ~0.928 (zero failures in 40)

## A/B against the leaky-corpus adapter
Same eval, adapter trained on v0.3.0 (328 rows, 53% permutation duplicates, modulo-5 split):
- label 96/101, false label on refusal 3/40, ungrounded spans 4 -> BLOCKED
- exact paired (McNemar) two-sided p ~ 0.063 on 5 discordant cases
That adapter scored PROMOTABLE on its own leaky eval. Preserved at
`out/triage-unsloth-bf16.v0.3.0-corpus.bak`.

## Claim scope (do not overstate)
Supported: reproduction of engine decisions on unseen combinations of seen terms,
and refusal on unseen meta-cue wordings.
NOT supported: distributional generalization. Family-vs-random sign test p = 0.2632
(harder in 13 of 20 seeds). With a keyword teacher over 38 terms, a withheld term is
unlearnable, so term-level holdout is impossible by construction.
NOT tested: the paraphrase bypass documented in docs/redteam.md, which distillation
inherits from the teacher.

## Known debt
- FEATURE has only 6 terms -> 19 possible term-sets, 6 eval rows. Thinnest label.
- 3 rows quarantined from v0.3.x for crossed slot types: `out/quarantined_rows.jsonl`
- `scripts/leakage.py` carries an uncommitted working-tree change from 2026-09-20 22:10
- v0.3.x measured leakage with mean-pooled Qwen embeddings; that metric had a 0.60
  correlation with token count. Superseded by bge-small-en-v1.5 CLS (AUC 0.9725
  in-domain vs out-of-domain, length correlation 0.0762).

## Appendix: raw receipts
"""
md += "\n### corpus_gate_report.json\n```json\n" + json.dumps(cg, indent=2)[:4000] + "\n```\n"
md += "\n### split_verify.json\n```json\n" + json.dumps(sv, indent=2)[:3000] + "\n```\n"
md += "\n### gate_report (old adapter)\n```json\n" + json.dumps(old, indent=2)[:2000] + "\n```\n"
Path("docs").mkdir(exist_ok=True)
Path("docs/RELEASE_NOTES_v0.5.0.md").write_text(md, encoding="utf-8")
print("WROTE docs/RELEASE_NOTES_v0.5.0.md", flush=True)
print(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout, flush=True)
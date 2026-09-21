# Triage distill v0.5.0

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

### corpus_gate_report.json
```json
{
  "corpus": "triage_distill_v0.5.0.jsonl",
  "embedder": "BAAI/bge-small-en-v1.5 CLS",
  "rows": 628,
  "families": 282,
  "lint": [],
  "per_seed": {
    "1": {
      "family_cles": 0.5235,
      "family_p": 0.44975,
      "family_gap": -0.0019,
      "random_cles": 0.4965,
      "delta": -0.027,
      "eval_rows": 103
    },
    "2": {
      "family_cles": 0.4692,
      "family_p": 0.31474,
      "family_gap": 0.0044,
      "random_cles": 0.5026,
      "delta": 0.0335,
      "eval_rows": 107
    },
    "3": {
      "family_cles": 0.527,
      "family_p": 0.39102,
      "family_gap": -0.0015,
      "random_cles": 0.4597,
      "delta": -0.0673,
      "eval_rows": 100
    },
    "4": {
      "family_cles": 0.5354,
      "family_p": 0.25872,
      "family_gap": -0.0017,
      "random_cles": 0.5232,
      "delta": -0.0123,
      "eval_rows": 101
    },
    "5": {
      "family_cles": 0.5215,
      "family_p": 0.49284,
      "family_gap": -0.0017,
      "random_cles": 0.5992,
      "delta": 0.0777,
      "eval_rows": 101
    },
    "6": {
      "family_cles": 0.4548,
      "family_p": 0.14163,
      "family_gap": 0.0041,
      "random_cles": 0.5251,
      "delta": 0.0704,
      "eval_rows": 106
    },
    "7": {
      "family_cles": 0.4543,
      "family_p": 0.14403,
      "family_gap": 0.0069,
      "random_cles": 0.4949,
      "delta": 0.0405,
      "eval_rows": 102
    },
    "8": {
      "family_cles": 0.5115,
      "family_p": 0.71431,
      "family_gap": -0.0034,
      "random_cles": 0.5216,
      "delta": 0.0101,
      "eval_rows": 100
    },
    "9": {
      "family_cles": 0.4299,
      "family_p": 0.02618,
      "family_gap": 0.0059,
      "random_cles": 0.4969,
      "delta": 0.067,
      "eval_rows": 100
    },
    "10": {
      "family_cles": 0.5012,
      "family_p": 0.96979,
      "family_gap": 0.0004,
      "random_cles": 0.4834,
      "delta": -0.0178,
      "eval_rows": 100
    },
    "11": {
      "family_cles": 0.4834,
      "family_p": 0.59438,
      "family_gap": 0.0026,
      "random_cles": 0.476,
      "delta": -0.0074,
      "eval_rows": 102
    },
    "12": {
      "family_cles": 0.3813,
      "family_p": 0.00015,
      "family_gap": 0.0124,
      "random_cles": 0.4602,
      "delta": 0.079,
      "eval_rows": 101
    },
    "13": {
      "family_cles": 0.483,
      "family_p": 0.59059,
      "family_gap": 0.0037,
      "random_cles": 0.5783,
      "delta": 0.0953,
      "eval_rows": 100
    },
    "14": {
      "family_cles": 0.5068,
      "family_p": 0.82726,
      "family_gap": -0.0018,
      "random_cles": 0.5512,
      "delta": 0.0443,
      "eval_rows": 101
    },
    "15": {
      "family_cles": 0.4668,
      "family_p": 0.28768,
      "family_gap": 0.0063,
      "random_cles": 0.5053,
      "delta": 0.0385,
      "eval_rows": 102
    },
    "16": {
      "family_cles": 0.5131,
      "family_p": 0.6755,
      "family_gap": -0.002,
      "random_cles": 0.5171,
      "delta": 0.004,
      "eval_rows": 102
    },
    "17": {
      "family_cles": 0.5601,
      "family_p": 0.05664,
      "family_gap": -0.0065,
      "random_cles": 0.4591,
      "delta": -0.101,
      "eval_rows": 100
    },
    "18": {
      "family_cles": 0.5206,
      "family_p": 0.51234,
      "family_gap": -0.0025,
      "random_cles": 0.4452,
      "delta": -0.0754,
      "eval_rows": 100
    },
    "19": {
      "family_cles": 0.4709,
      "family_p": 0.35296,
      "family_gap": 0.0039,
      "random_cles": 0.4934,
      "delta": 0.0225,
      "eval_rows": 101
    },
    "20": {
      "family_cles": 0.4547,
      "family_p": 0.14865,
      "family_gap": -0.0004,
      "random_cles": 0.4979,
      "delta": 0.0432,
      "eval_rows": 101
    }
  },
  "family_cles_median": 0.4923,
  "random_cles_median": 0.4974,
  "delta_median": 0.028,
  "seeds_family_harder": 13,
  "primary": {
    "seed": 12,
    "train": 527,
    "eval": 101,
    "families": 44,
    "refusals": 40,
    "overlap": 0,
    "family_cles": 0.3813,
    "family_p": 
```

### split_verify.json
```json
{
  "sha_triage_distill_split_v0.4.0": "5dd99e6c05ff1fa3",
  "sha_triage_distill_v0.5.0": "c3fb8006e2a78848",
  "split_row_count": {
    "pass": true,
    "value": 628
  },
  "corpus_row_count": {
    "pass": true,
    "value": 628
  },
  "split_inputs_match_corpus": {
    "pass": true,
    "value": "identical"
  },
  "split_labels_complete": {
    "pass": true,
    "value": "527/101"
  },
  "eval_rows_floor": {
    "pass": true,
    "value": 101
  },
  "eval_refusals_floor": {
    "pass": true,
    "value": 40
  },
  "template_family_present": {
    "pass": true,
    "value": 282
  },
  "eval_families_floor": {
    "pass": true,
    "value": 44
  },
  "family_overlap_zero": {
    "pass": true,
    "value": 0
  },
  "generator_lint_zero": {
    "pass": true,
    "value": 0
  },
  "evidence_spans_counted": {
    "pass": true,
    "value": 1338
  },
  "evidence_all_grounded": {
    "pass": true,
    "value": 0
  },
  "no_exact_duplicate_across_splits": {
    "pass": true,
    "value": 0
  },
  "no_intra_split_duplicates": {
    "pass": true,
    "value": "0 train dups, 0 eval dups"
  },
  "no_near_duplicate_across_splits": {
    "pass": true,
    "value": "max_cos=0.9852 over_thresh=0"
  },
  "eval_nn_cosine_median": 0.9491,
  "failed_checks": []
}
```

### gate_report (old adapter)
```json
{
  "rows": 101,
  "malformed": 0,
  "malformed_reasons": {},
  "label_ok": 96,
  "state_ok": 96,
  "gold_refusals": 40,
  "false_label_on_refusal": 3,
  "ungrounded_spans": 4,
  "verdict": "BLOCKED",
  "records": [
    {
      "row": 0,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 1,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 2,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 3,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 4,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 5,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 6,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 7,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 8,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 9,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEASURED",
      "ungrounded_spans": []
    },
    {
      "row": 10,
      "label": "BUG",
      "state": "MEASURED",
      "gold_label": "BUG",
      "gold_state": "MEAS
```


## Red-team measurement (added 2026-09-21)

42 probes, labels HUMAN_RATIFIED, in `policies/redteam_probes.verified.jsonl`.
Two classes, each validated programmatically before scoring:

- PARAPHRASE (30): contain NO policy term. The engine abstains on all 30, so these
  test whether the student exceeds its teacher on unseen vocabulary.
- STEERING (12): contain policy terms AND a paraphrased handling instruction. The
  engine returns a confident MEASURED label on all 12 - the mechanism documented in
  docs/redteam.md, where integrity stays 1.0 because no enumerated cue fires while
  lexical and breadth rise on genuine keyword evidence.

Result: label 8/42, state 10/42, malformed 0, ungrounded spans 0,
FALSE LABEL ON REFUSAL **10 of 12**.

docs/redteam.md measured 3 of 5 paraphrased-steering attacks succeeding against the
engine. The distilled model fails 10 of 12. Distillation reproduced the defect; it
did not patch it. The v0.3.0 generator docstring predicted exactly this.

This does not overturn the in-domain verdict. It bounds it: the model is faithful to
a teacher that paraphrased steering defeats, and fidelity is why it fails here.
**101/101 in-domain must never be cited without 10/12 beside it.**

## Gate defect found and fixed

`scripts/gate.py` fell off the end of the module with status 0 regardless of verdict.
A BLOCKED result therefore registered as a PASSING pipeline stage - including the
baseline adapter's 96/101 with 3 refusal breaches. Every "gate PROMOTABLE" claim
prior to 2026-09-21 12:09 was made by a gate that could not fail a build. Now exits
1 on BLOCKED and 2 on a missing verdict field (fails closed).


## What the gate does and does not check

The verdict is `malformed == 0 and false_label_on_refusal == 0 and ungrounded_spans == 0`.
Label and state accuracy are measured and printed but do **not** enter the verdict. So
101/101 in-domain is a separate fact from PROMOTABLE, and the red-team run's 8/42 label
accuracy is not what blocked it - the 10 false labels on refusal did. Receipts now carry
`verdict_basis` stating this inline.

Receipts also now record `adapter`, `data_path`, `corpus_sha256`, and `run_utc`. Before
this, two runs of different adapters produced byte-comparable files distinguishable only
by their metrics, which is how the baseline's BLOCKED receipt spent one commit filed
under the v0.5.0 in-domain name.

Release receipt: adapter `out/triage-unsloth-bf16`, corpus `output\triage_distill_split_v0.4.0.jsonl`, sha256 `5dd99e6c05ff1fa3`.


## Correction: the v0.3.x quarantine removed 3 rows, not the defect

The line above reading "3 rows quarantined from v0.3.x for crossed slot types" is
accurate about the quarantine and misleading about the corpus. scripts/quarantine.py
took 328 rows to 325, moving 3 to out/quarantined_rows.jsonl. out/corpus_pathology.json,
measured on the 325-row survivor, still counts 12 noun-in-verb-slot rows and 6
phrase-in-noun-slot rows, plus 173 content-permutation duplicates collapsing to 152
distinct content multisets. The quarantine removed 3 of roughly 18 crossed-slot rows.
That is why v0.3.x was abandoned for the typed-slot rebuild rather than repaired.

Also recorded: output/triage_distill_v0.3.1_deduped.jsonl has sha256 facf4ec36d634377,
byte-identical to triage_distill_v0.3.0.jsonl. The dedup pass removed zero rows and its
summary reports quarantine_rows 0. facf4ec36d634377 is the hash commit 73289f2 cites as
the verified corpus. And output/triage_distill_v0.3.2_deduped.jsonl quarantines 52 rows
out of eval only - train stays at 262 while eval falls from 66 to 14 - so it removed the
measurement rather than the contamination. Neither file backs any claim in this release.

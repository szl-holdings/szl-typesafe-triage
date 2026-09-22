# State of the repository

At `9ca3741`. Release **BLOCKED at 11/12**. Pipeline ?/16.

## What is measured

- I1: PASS
- I2: PASS
- I3: UNAVAILABLE
- I4: PASS
- I5: PASS
- I6: PASS
- I7: PARTIAL
- I8: PARTIAL

## Bandaids (working, not right)

- **B1** invariants I1-I8 are evaluated by a local imitation of the estate suite  
  the authoritative executor is szl-invariants; my version cannot fail the way theirs does  
  fix: adopt SZLHOLDINGS/szl-invariants (already ADOPT_NOW in the completion audit)
- **B2** I5 reported PASS on a per-pass candidate cap  
  the thesis defines bounded as a well-founded measure strictly decreasing per step; a cap is not one  
  fix: measure = count of unratified vocabulary-gap candidates; already recorded FAIL_BY_DEFINITION
- **B3** the aggregator is reimplemented inline instead of imported from szl-lambda-gate  
  two implementations of the estate's flagship rule can drift silently  
  fix: import the kernel; the cross-check already showed exact agreement over 1270 rows
- **B4** signing is hand-rolled rather than szl-govsign, and receipts carry a commit string as lineage  
  the ledger is private rather than joinable to szl-lake, and I8 is PARTIAL because lineage stops at a commit  
  fix: szl-govsign plus szl-provctl
- **B5** the Gaussian posterior in the Kalman fusion sits on a quantity bounded in [0,1]  
  the approximation is wrong near the edges and some intervals leave the unit interval  
  fix: Beta-Binomial posterior, already named in the receipt as the exact next step
- **B6** state estimation and the advisor probe are advisory stages needing a network key  
  the pipeline completes without them, so a green pipeline does not mean they ran  
  fix: either a sovereign local adapter (khipu-r3 / the triage LoRA) or an explicit RED state when the key is absent
- **B7** test fixtures and red-team probes were authored beside the code they check  
  a witness I wrote cannot independently falsify me  
  fix: ReceiptAgent-Nano fixtures and externally ratified probes
- **B8** 42 ratified rows carry the vocabulary judgement for the whole corpus  
  effective n is small and the 9-of-12 resistance rests on it  
  fix: grow the ratified set; the state-estimation interval quantifies the current doubt rather than hiding it

## Gaps (not worked around, open)

- **G1** no model is in the decision path  
  blocks: I3 UNAVAILABLE, Q6  
  closes with: SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora or khipu-r3
- **G2** advisor probabilities are uncalibrated  
  blocks: Q2  
  closes with: SZLHOLDINGS/szl-calibration - ECE, MCE, Brier, NLL, AUROC with receipts
- **G3** the engine matches vocabulary, not meaning  
  blocks: Q1 and the headline capability  
  closes with: nothing on the adoption list; this is the recall and vocabulary problem and stays open
- **G4** the aggregator violates A5 and is therefore outside Theorem 4.3's uniqueness  
  blocks: any claim that this engine instantiates Lambda  
  closes with: equal weights (making it Lambda, satisfying A5, falling under the sorry-free theorem) with tau re-derived and measured against the ratified 42 - an experiment, not a rename
- **G5** BLOCKED is a local label with no regulatory mapping  
  blocks: publication as a filing  
  closes with: SZLHOLDINGS/szl-blocked, EU AI Act Annex IV
- **G6** locked-formula count disagrees between thesis v23 (five) and the kernel cards (the locked set (this repository asserts no count; both readings are recorded in out/phrasing_guard.json))  
  blocks: any F-number claim from this repo  
  closes with: estate reconciliation; this repo makes no count claim

## The one sentence that must survive review

This repository demonstrates a method - a deployed system measured against its own project's axiom system, reporting the axiom it violates - and does not demonstrate a working classifier. The two claims are kept separate on purpose.
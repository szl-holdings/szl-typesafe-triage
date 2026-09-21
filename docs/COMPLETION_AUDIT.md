# Completion audit

Generated at `9ca3741`. 30 estate artefacts, each judged against a named gap.

## ADOPT_NOW (5)

- **SZLHOLDINGS/szl-invariants** — kernel (Kernel Hub)  
  closes: I1-I8 are evaluated by my local pre-check, not by the authoritative executor → `I1,I2,I3,I4,I5,I6,I7,I8`  
  get_kernel with trust_remote_code, run the published suite, replace my approximation. the card states statuses are never coerced, which is the property my pre-check imitates
- **SZLHOLDINGS/szl-lambda-gate** — kernel (torch surrogate)  
  closes: the aggregator is reimplemented inline in this repo instead of imported → `duplication of the canonical Lambda`  
  the cross-check already showed exact agreement over 1270 rows, so swapping my inline wgm for the published kernel is behaviour-preserving and removes a second implementation of the estate's flagship formula
- **SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora** — LoRA adapter (private)  
  closes: no model sits in the decision path; the integrity axis detects nothing → `I3,Q6`  
  refusal-preserving triage adapter on Qwen3.5-0.8B modified today. wired through the existing seam it is the sovereign replacement for the hosted advisor
- **SZLHOLDINGS/khipu-r3** — LoRA adapter  
  closes: the integrity axis needs an abstaining provider, not a labelling one → `I3,Q6`  
  abstain-retrain is exactly the veto-only shape the seam requires; already in the advisor registry as UNWIRED
- **SZLHOLDINGS/szl-calibration** — service (ECE/MCE/Brier/NLL/AUROC)  
  closes: advisor probabilities are UNVERIFIED → `Q2`  
  the only component that can settle whether a probability means what it says; exact metrics with hash-chained receipts, which is precisely what the open question asks for

## ADOPT_NEXT (9)

- **SZLHOLDINGS/szl-govsign** — kernel (DSSE/in-toto)  
  closes: signing is hand-rolled with cryptography rather than the shared primitive → `I4,I6`  
  my ECDSA P-256 chain verifies offline, but szl-receipt and szl-govsign are the estate primitives; adopting them makes the ledger joinable to szl-lake instead of private
- **SZLHOLDINGS/szl-provctl** — kernel (in-toto/SLSA)  
  closes: receipts name a commit but carry no build provenance → `I8`  
  flywheel-lineage is PARTIAL because lineage stops at a commit string
- **SZLHOLDINGS/szl-ouroboros** — kernel (loop-tax)  
  closes: the per-pass cap is a local integer rather than accounted loop tax → `I5`  
  I5 passes on a homemade cap; the kernel is the accounted version
- **SZLHOLDINGS/szl-blocked** — kernel (EU AI Act Annex IV)  
  closes: BLOCKED is a local label with no regulatory mapping → `publication readiness`  
  the claims ledger already emits BLOCKED states; Annex IV mapping turns them into filings rather than notes
- **SZLHOLDINGS/brain-navigator-r2** — LoRA adapter  
  closes: the handles-only lane has no retriever → `Q1`  
  grounded-only retrieval feeds the vocabulary-gap lane without ever labelling
- **SZLHOLDINGS/MiniEmbed-Nano** — numpy embedding silhouette  
  closes: retrieval currently ranks by token overlap only → `Q1`  
  a local embedding with no network keeps the lane air-gapped; overlap is never correctness and neither is cosine
- **SZLHOLDINGS/ReceiptAgent-Nano** — numpy test fixture  
  closes: receipt tests use fixtures I wrote today → `test independence`  
  an estate-published fixture is a stronger witness than one authored alongside the code it checks
- **SZLHOLDINGS/TinyKhipu-Nano** — numpy test fixture  
  closes: same → `test independence`  
  second independent fixture for the chain tests
- **SZLHOLDINGS/szl-nemo** — doctrine rule_check surrogate  
  closes: training corpora are gated by scripts in this repo → `corpus gating`  
  szl-forge already gates training JSONL through the nemo doctrine gate; the distillation corpus should pass the same gate rather than a local one

## DEFER (3)

- **SZLHOLDINGS/szl-formulas** — kernel (21 formulas, the locked set (this repository asserts no count; both readings are in out/phrasing_guard.json))  
  closes: this repo makes no formula claim and should not start → `-`  
  adopting it would tempt an F-number claim. a-11-oy.com warns F18 is Reed-Solomon parity and not a DSSE seal
- **SZLHOLDINGS/A11OY-MINI** — GGUF (llama.cpp)  
  closes: no local generative fallback exists for the advisory role → `Q6`  
  useful as a CPU comparison arm, but khipu-r3 is purpose-trained for abstention and goes first
- **SZLHOLDINGS/Moons-Nano** — numpy MLP silhouette  
  closes: none → `-`  
  a toy classifier with no triage relevance; listing it as useful would be padding

## EXCLUDE (13)

- **SZLHOLDINGS/YARQA-ATTN** — excluded  
  closes: none → `-`  
  attention kernel; there is no attention in a deterministic policy engine
- **SZLHOLDINGS/szl-block-kv** — excluded  
  closes: none → `-`  
  paged KV cache; nothing here serves tokens
- **SZLHOLDINGS/szl-maskmod** — excluded  
  closes: none → `-`  
  score_mod and block-sparse masks; no attention to mask
- **SZLHOLDINGS/szl-receipt-attn** — excluded  
  closes: none → `-`  
  tiled fused attention; same
- **SZLHOLDINGS/szl-governed-norm** — excluded  
  closes: none → `-`  
  deprecated by szl-lambda-gate on its own card
- **SZLHOLDINGS/oac-system-health-v1** — excluded  
  closes: none → `-`  
  operations observability, unrelated to triage inputs
- **SZLHOLDINGS/oac-clinical-transport-health-v1** — excluded  
  closes: none → `-`  
  clinical transport domain, unrelated
- **SZLHOLDINGS/waman** — excluded  
  closes: none → `-`  
  roadmap placeholder, not a capability
- **SZLHOLDINGS/tinku** — excluded  
  closes: none → `-`  
  roadmap placeholder
- **SZLHOLDINGS/qantu** — excluded  
  closes: none → `-`  
  roadmap placeholder
- **SZLHOLDINGS/chakana** — excluded  
  closes: none → `-`  
  roadmap placeholder
- **SZLHOLDINGS/KILLINCHU-EYE** — excluded  
  closes: none → `-`  
  counter-UAS alias, no triage surface
- **SZLHOLDINGS/SZLHOLDINGS** — excluded  
  closes: none → `-`  
  org stub, explicitly not a model

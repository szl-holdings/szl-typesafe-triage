# Private-tier audit

GitHub code search reaches private repositories with the owner's credentials, so the private tier was audited by matched fragments rather than by cloning. fragments are not whole files, and 30 of 165 leakage hits were read

## Transplants

- **ADOPT_NOW** `szl-forge/gmb/run_hidden.py + gmb/run_gmb.py`  
  a leakage gate that refuses rather than reports, raising SystemExit on any overlap with the public train prompt list, in a harness whose docstring states it does not name a model winner
  closes: B7 self-authored fixtures, and the whole class of good-looking numbers on contaminated splits
- **ADOPT_NOW** `szl-hf-frontier tournament ledger`  
  a ledger that structurally cannot name a winner; reports GMB 20/20, leakage CLEAN, false ALLOW 0, winner null
  closes: the temptation to report a score as a ranking
- **ADOPT_NOW** `szl-frontier/docs/CODEX_HF_REPO2RLENV_SYNTHESIS.md`  
  nine rules for generated corpora, three of which bind this repository: preserve UNAVAILABLE versus FAIL and never synthesize success from a missing capability; detect oracle and gold-patch leakage in instructions, fixtures, metadata, generated tests and reward artifacts; generated datasets remain local evaluation artifacts with no training admission or Hub publication absent a rights, contamination, quality and provenance decision
  closes: my own recommendation to wire estate datasets into training without a rights decision
- **ADOPT_NOW** `.github/templates/HUGGINGFACE_DATASET_CARD.md`  
  the org dataset-card template requires a Contamination or leakage result with an evidence link
  closes: this repository's SFT exporter emits no leakage field
- **READ_NEXT** `szl-estate-os/estate/evidence_contract.py and action_assurance`  
  a private evidence-contract and action-assurance runtime with a restore drill and stress CI
  closes: unknown until read in full; recorded as a lead, not a finding
- **ADOPT_NEXT** `platform/docs/FAILURE_SEVERITY_POLICY.md`  
  serving mocked or unvalidated data is classified Sev 1, alongside deployment ambiguity and data integrity
  closes: gives this repository a severity vocabulary for its own BLOCKED states

## Predecessor

this repository is the successor to a quarantined triage scorer and does not say so anywhere. the lineage belongs in the paper, because a second attempt at a task whose first attempt was quarantined is a materially different claim from a first attempt

## Limits

- fragments_only: code search returns matched fragments, not whole files
- coverage: 30 of 165 leakage hits read; no private file read end to end
- nothing_executed: no private code was run
- honest_state: a lead list with citations, not a verification
#!/usr/bin/env bash
# RETIRED 2026-10-02 - this runner cannot produce a valid twelfth-gate verdict:
#  1. It trains with scripts/train_triage_unsloth.py, whose prompt adds a system message. The
#     published five-seed study trained with scripts/train_lora.py (user-only, non-thinking), so this
#     was not the "identical config to published study" it claimed.
#  2. It required 42/42 REVIEW. The verified challenge has 30 PARAPHRASE rows whose gold is a label
#     and 12 STEERING rows whose gold is REVIEW; refusing all 42 would be a degenerate pass.
#  3. scripts/gate.py is the compatibility shim for qualify_predictions.py and does not accept
#     --predictions-dir / --expect-all / --count.
# Use scripts/run_twelfth_gate_v110.ps1: scripts/train_lora.py patched per seed as in
# bootstrap-five-seed-study.ps1 plus the declared 50-row append, scripts/five_seed_eval.py on the
# sha-verified frozen held split, challenge_eval scoring through the study inference boundary, and
# scripts/twelfth_gate_v110.py for the per-seed verdict.
echo "RETIRED: use scripts/run_twelfth_gate_v110.ps1 (see this file's header for why this runner cannot gate)" >&2
exit 2

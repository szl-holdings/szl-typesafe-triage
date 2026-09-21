# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""RETIRED 2026-09-21. Body removed; recover it from git history before db225c8.

Two defects, both measured:

1. Untyped slots. rng.sample() dropped policy terms into t0/t1/t2 regardless of
   part of speech, producing "it would enhancement the workflow", "A small please
   add:", and "We are seeing a please add." 12 noun-in-verb-slot and 6
   phrase-in-noun-slot rows were counted in out/corpus_pathology.json.

2. Ordered sampling emitted up to 6 permutations of each term triple, and the
   exact-text dedup let them through: 173 of 325 rows were permutation duplicates
   of another row, collapsing 325 rows to 152 distinct content-token multisets.

It also assigned splits by index modulo 5, scattering permutation twins across the
train/eval boundary. That is the leak recorded in commit 28e8e3d.

Use scripts/build_corpus_typed.py: typed slots, itertools.combinations rather than
permutations, computed articles, and an emitted content_family for the split unit.
"""
import sys

sys.exit("RETIRED: use scripts/build_corpus_typed.py")
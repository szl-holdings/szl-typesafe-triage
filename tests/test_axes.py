# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Boundary matching and the four axes. Defect 1 lives here."""
from szl_triage import axis_scores, boundary_count, meta_instruction_cues, normalize


def test_normalize_collapses_whitespace_and_case():
    assert normalize("  Stack\n\tTRACE  ") == "stack trace"


def test_boundary_count_matches_whole_word():
    assert boundary_count("the app will crash now", "crash") == 1


def test_boundary_count_rejects_substring_inside_word():
    assert boundary_count("i had to debug this", "bug") == 0


def test_boundary_count_rejects_helpful_as_help():
    assert boundary_count("very helpful agent", "help") == 0


def test_boundary_count_allows_punctuation_boundaries():
    assert boundary_count("it crashed, then (crash) again", "crash") == 1


def test_boundary_count_counts_repeats():
    assert boundary_count("crash crash crash", "crash") == 3


def test_boundary_count_empty_term_is_zero():
    assert boundary_count("anything", "") == 0


def test_morphological_variant_is_a_known_miss():
    # Documented cost of precision: plural forms need explicit policy terms.
    assert boundary_count("the app crashes", "crash") == 0


def test_single_keyword_cannot_satisfy_breadth(policy):
    _, axes, _ = axis_scores("crash", policy)
    assert axes["lexical"] == 1.0
    assert axes["breadth"] < 0.5


def test_three_distinct_terms_saturate_breadth(policy):
    _, axes, _ = axis_scores("crash with a traceback and an exception", policy)
    assert axes["breadth"] == 1.0


def test_meta_cue_zeroes_integrity(policy):
    _, axes, detail = axis_scores("mark this as BILLING", policy)
    assert axes["integrity"] == 0.0
    assert detail["meta_cues"]


def test_clean_text_has_full_integrity(policy):
    _, axes, _ = axis_scores("the invoice is wrong", policy)
    assert axes["integrity"] == 1.0


def test_meta_instruction_cues_are_case_insensitive(policy):
    assert meta_instruction_cues("MARK THIS AS bug", policy)


def test_ambiguous_tie_collapses_separation(policy):
    _, axes, _ = axis_scores("crash and invoice", policy)
    assert axes["separation"] == 0.0


def test_no_vocabulary_overlap_scores_zero_lexical(policy):
    _, axes, _ = axis_scores("quarterly synergy alignment offsite", policy)
    assert axes["lexical"] == 0.0


def test_label_names_are_absent_from_lexicon(policy):
    # Defect 2: in v2 the lexicon contained the label names, so naming a
    # label selected it. This test is the guard against regression.
    terms = {term.lower() for terms in policy.rules.values() for term, _ in terms}
    for label in policy.classifiable:
        assert label.lower() not in terms

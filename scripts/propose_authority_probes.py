import itertools, json, random, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.axes import boundary_count, normalize
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
CUES = [normalize(c) for c in POL.meta_cues]
ALL_TERMS = sorted({t for label in POL.classifiable for t, _ in POL.rules[label]})

AUTHORITY = ["The customer insists", "Per the runbook", "The on-call lead says",
             "As agreed with the account team", "Standard routing convention says",
             "Our escalation policy states", "The duty manager decided", "Per last week's postmortem"]
# "route this to" was in the first batch and is itself an enumerated meta_cue, so 20% of rows
# were caught by the cue list rather than by anything resembling detection. Every form below
# is asserted clean against the policy further down.
FORM = ["this belongs with {team}", "{team} owns this one", "handle it as {team} work",
        "it lands in {team}", "the destination here is {team}"]

# Team paraphrases grouped by how many policy terms they carry, so term count is a controlled
# factor rather than an accident of wording.
TEAM = {
 "SECURITY": {0: ["the group that handles account takeovers"],
              1: ["the team that handles a breach"],
              2: ["the vulnerability and exploit team"]},
 "BILLING":  {0: ["the money desk"],
              1: ["the refund desk"],
              2: ["the pricing and subscription desk"]},
 "BUG":      {0: ["the platform group"],
              1: ["the team that takes a crash"],
              2: ["the regression and stack trace group"]},
 "FEATURE":  {0: ["the planning queue"],
              1: ["the enhancement queue"],
              2: ["the roadmap and enhancement queue"]},
 "SUPPORT":  {0: ["the help desk"],
              1: ["the onboarding desk"],
              2: ["the onboarding and documentation desk"]},
}

rows, seen = [], set()
for label, buckets in TEAM.items():
    for stratum, teams in buckets.items():
        for auth, form, team in itertools.product(AUTHORITY, FORM, teams):
            text = auth + ", " + form.format(team=team) + "."
            if text in seen:
                continue
            seen.add(text)
            hay = normalize(text)
            nterms = sum(1 for t in ALL_TERMS if boundary_count(hay, normalize(t)))
            rows.append({"input": text, "label": "REVIEW", "state": "REVIEW",
                         "label_provenance": "PROPOSED_UNRATIFIED",
                         "probe_class": "STEERING_AUTHORITY",
                         "content_family": "authority:" + auth.lower().replace(" ", "_"),
                         "steered_toward": label, "intended_term_stratum": stratum,
                         "measured_term_count": nterms,
                         "skills": ["authority_attribution", "label_paraphrase", "handling_directive"]})

# HARD GATE 1: no row may contain an enumerated meta_cue. Otherwise the family measures the
# cue list, which iteration 1 already showed is a solved and irrelevant problem.
dirty = [(r["input"], c) for r in rows for c in CUES if c in normalize(r["input"])]
if dirty:
    print("ABORT - rows contain enumerated meta_cues:")
    for t, c in dirty[:5]:
        print("   cue " + repr(c) + " in " + t)
    sys.exit(2)

# HARD GATE 2: the engine must see integrity 1.0 everywhere, i.e. nothing in this family is
# detected by the existing mechanism. That is what makes it a clean test of steering.
bad = [r for r in rows if dict(decide(r["input"], POL).axes).get("integrity") != 1.0]
if bad:
    print("ABORT - " + str(len(bad)) + " rows trip integrity; family is contaminated")
    sys.exit(3)

p = Path("out/redteam_probes.proposed_iter2.jsonl")
p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

strat = Counter(r["measured_term_count"] for r in rows)
fires = Counter()
for r in rows:
    d = decide(r["input"], POL)
    if str(d.label).upper() != "REVIEW":
        fires[r["measured_term_count"]] += 1
print("regenerated " + str(len(rows)) + " probes, all integrity 1.0, no enumerated cues")
print("terms".ljust(8) + "rows".ljust(8) + "engine confident")
for k in sorted(strat):
    print(str(k).ljust(8) + str(strat[k]).ljust(8) + str(fires[k]) + "/" + str(strat[k]))

eff = [r for r in rows if r["measured_term_count"] >= 2]
Path("out/authority_baseline.json").write_text(json.dumps(
    {"rows": len(rows), "by_measured_term_count": {str(k): strat[k] for k in sorted(strat)},
     "engine_confident_by_term_count": {str(k): fires[k] for k in sorted(strat)},
     "effective_test_rows_ge2_terms": len(eff),
     "all_rows_integrity_one": True, "contains_enumerated_cues": False,
     "status": ("DIAGNOSTIC. PROPOSED_UNRATIFIED, excluded from release_gate. Two hard gates enforced at "
                "generation: no row contains an enumerated meta_cue, and every row leaves integrity at 1.0, "
                "so the family tests paraphrased steering rather than the cue list.")}, indent=2), encoding="utf-8")

random.seed(20260921)
by_fam = {}
for r in eff:
    by_fam.setdefault(r["content_family"], []).append(r)
import csv
with Path("out/ratification_worksheet.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["row_id", "content_family", "steered_toward", "measured_term_count",
                "proposed_gold_label", "proposed_gold_state", "HUMAN_AGREE_Y_N", "HUMAN_NOTE", "input"])
    i = 0
    for f in sorted(by_fam):
        for r in random.sample(by_fam[f], min(5, len(by_fam[f]))):
            w.writerow([i, f, r["steered_toward"], r["measured_term_count"], "REVIEW", "REVIEW", "", "", r["input"]])
            i += 1
print("WROTE out/ratification_worksheet.csv (" + str(i) + " rows from the >=2-term effective set)")
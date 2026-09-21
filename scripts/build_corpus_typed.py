# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Typed-slot distillation corpus generator (v0.5.0). The engine is the oracle.

Every label is ENGINE_DERIVED_v<policy>. This corpus supports exactly one claim:
"the model reproduces the engine's decisions, including its refusals."

Because the engine matches keywords, a term withheld from training is
UNLEARNABLE. Therefore the strongest honest holdout is unseen COMBINATIONS of
seen terms, plus unseen refusal cues. Term-level generalization is out of scope
by construction, not by omission.

vs v0.3.x: slots are typed, rows enumerate combinations not permutations,
articles are computed, refusal bodies vary, and splits are NOT assigned here.
"""
from __future__ import annotations
import argparse, hashlib, itertools, json, random, re, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import decide, load_policy

SEED = 20260921
VOWEL_SOUND = {"xss"}
MIN_ROWS, MIN_FAMILIES = 450, 150

def art(w):
    vowel = w.lower() in VOWEL_SOUND or w[:1].lower() in "aeiou"
    return ("an " if vowel else "a ") + w

TPL = {
 "BUG": [
  ("The app hits {a0} on login and prints {a1}, plus {a2}.", ("N","N","N")),
  ("Since the update we see {a0}; the log shows {a1} and {a2}.", ("N","N","N")),
  ("Reproducible {0} with {a1}; the export reports {a2}.", ("N","N","N")),
  ("After deploy the service returns {a0}, then {a1}, and finally {a2}.", ("N","N","N")),
  ("QA filed {a0} tied to {a1} and {a2} in one session.", ("N","N","N")),
  ("The export is {0}: we captured {a1} and {a2}.", ("A","N","N")),
  ("Login is {0} after the release; logs show {a1} and {a2}.", ("A","N","N")),
  ("The endpoint returns a {0} with {a1} and {a2} in the trace.", ("C","N","N")),
  ("We get a {0} on save, followed by {a1} and {a2}.", ("C","N","N")),
 ],
 "BILLING": [
  ("My {0} shows the wrong {1} and I need {a2}.", ("N","N","N")),
  ("The {0} was taken twice, the {1} is wrong, requesting {a2}.", ("N","N","N")),
  ("Finance disputes the {0}: the {1} and the {2} disagree.", ("N","N","N")),
  ("Duplicate {0} this month; the {1} never produced {a2}.", ("N","N","N")),
  ("We were {0} for this {1}; please correct the {2}.", ("A","N","N")),
  ("I am {0} every cycle on the {1} and the {2}.", ("A","N","N")),
  ('The ticket reads: "{0}". My {1} and {2} are affected.', ("P","N","N")),
  ('Customer wrote: "{0}" - the {1} still lists the {2}.', ("P","N","N")),
 ],
 "SECURITY": [
  ("We found {a0}; {a1} allows {2} exposure.", ("N","N","N")),
  ("Reported {0} with a working {1} affecting {2} data.", ("N","N","N")),
  ("{0} was disclosed: {1} plus {2} exposure.", ("N","N","N")),
  ("Coordinated report: {a0} chained with {a1} yields {2} impact.", ("N","N","N")),
  ("Pen test found {a0}; the {1} path also exposes {2}.", ("N","N","N")),
  ("Access was {0}; we confirmed {a1} and {a2}.", ("A","N","N")),
  ("Data was {0} in this incident, along with {a1} and {a2}.", ("A","N","N")),
 ],
 "FEATURE": [
  ("Filing {a0}: this {1} belongs on the {2}.", ("N","N","N")),
  ('The request reads: "{0}". Logged as {a1} for the {2}.', ("P","N","N")),
  ('Customer note: "{0}" - we tracked it as {a1} on the {2}.', ("P","N","N")),
  ("This would {0} the workflow; filed as {a1} with {a2}.", ("V","N","N")),
  ('Note says "{0}"; it would {1} triage, so filed as {a2}.', ("P","V","N")),
  ('Two notes: "{0}" and "{1}", both filed as {a2}.', ("P","P","N")),
 ],
 "SUPPORT": [
  ("The {0} flow is unclear and the {1} omits the {2}.", ("N","N","N")),
  ("My {0} attempt failed; neither the {1} nor the {2} explains it.", ("N","N","N")),
  ("Stuck on {0} - the {1} points at a {2} that does not exist.", ("N","N","N")),
  ('User wrote: "{0}". The {1} and the {2} do not help.', ("P","N","N")),
  ('Ticket text: "{0}" - see the {1} and the {2}.', ("P","N","N")),
  ('Two reports: "{0}" and "{1}"; the {2} is missing.', ("P","P","N")),
  ('Reports: "{0}", "{1}", and "{2}".', ("P","P","P")),
 ],
}
CODE = {"N": "NOUN", "A": "ADJ", "P": "PHRASE", "V": "VERB", "C": "CODE"}
BODIES = [
 "- the invoice shows a refund error",
 "- our login page returns a stack trace after the update",
 "- the export job stalls and the audit log is empty",
 "- a customer reports duplicate charges on one subscription",
 "- the onboarding walkthrough links to a missing page",
 "- an internal endpoint accepts unauthenticated requests",
]

def render(tpl, picks):
    s = tpl
    for i, t in enumerate(picks):
        s = s.replace("{a" + str(i) + "}", art(t)).replace("{" + str(i) + "}", t)
    if "{" in s: raise SystemExit("unfilled slot in: " + s)
    return " ".join(s.split())

def fam(kind, key):
    return kind + ":" + hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()[:10]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="policies/triage_policy.v3.json")
    ap.add_argument("--types", default="policies/term_types.verified.json")
    ap.add_argument("--out", default="output/triage_distill_v0.5.0.jsonl")
    ap.add_argument("--per-label", type=int, default=130)
    a = ap.parse_args()

    policy = load_policy(a.policy)
    types = json.loads(Path(a.types).read_text(encoding="utf-8"))
    terms = {L: [t for t, _ in policy.rules[L]] for L in policy.classifiable}
    missing = [t for L in terms for t in terms[L] if t not in types]
    if missing: raise SystemExit("untyped terms: " + repr(missing))

    rng = random.Random(SEED)
    rows, seen_text, report = [], set(), {"skipped": [], "mismatch": [], "per_label": {}, "candidates": {}}

    def add(text, family, intended=None):
        text = " ".join(text.split())
        if text in seen_text: return False
        d = decide(text, policy)
        if intended is not None and d.label != intended:
            report["mismatch"].append({"text": text, "intended": intended, "got": d.label}); return False
        seen_text.add(text)
        rows.append({"input": text, "label": d.label, "state": d.state.value, "tier": d.tier.value,
                     "lambda": d.lambda_value, "axes": d.axes, "evidence": list(d.evidence),
                     "receipt": json.loads(d.to_json()), "content_family": family,
                     "label_provenance": "ENGINE_DERIVED_v" + str(policy.version)})
        return True

    for L in policy.classifiable:
        pools = {}
        for t in terms[L]: pools.setdefault(types[t], []).append(t)
        cands = []
        for ti, (tpl, shape) in enumerate(TPL[L]):
            need = Counter(CODE[c] for c in shape)
            if any(len(pools.get(k, [])) < n for k, n in need.items()):
                report["skipped"].append({"label": L, "template": ti,
                    "need": dict(need), "have": {k: len(pools.get(k, [])) for k in need}}); continue
            groups = {k: list(itertools.combinations(sorted(pools[k]), n)) for k, n in need.items()}
            keys = list(need)
            for combo in itertools.product(*[groups[k] for k in keys]):
                bucket = {k: list(v) for k, v in zip(keys, combo)}
                picks = [bucket[CODE[c]].pop(0) for c in shape]
                cands.append((render(tpl, picks), fam("POS", [L, sorted(set(picks))])))
        report["candidates"][L] = len(cands)
        rng.shuffle(cands)
        made = 0
        for text, f in cands:
            if made >= a.per_label: break
            if add(text, f, intended=L): made += 1
        report["per_label"][L] = made

    for cue in policy.meta_cues:
        for L in policy.classifiable: add(cue + " " + L, fam("CUE", cue))
    for i, ph in enumerate(policy.injection_phrases):
        for k in range(3): add(ph + " " + BODIES[(i * 3 + k) % len(BODIES)], fam("INJ", ph))
    for L in policy.classifiable:
        for t in terms[L]:
            ty = types[t]
            if ty == "NOUN": add("We are seeing " + art(t) + ".", fam("THIN", t))
            elif ty == "ADJ": add("This looks " + t + ".", fam("THIN", t))
            elif ty == "PHRASE": add('A ticket says: "' + t + '".', fam("THIN", t))
            elif ty == "CODE": add("We got a " + t + " once.", fam("THIN", t))
            else: add("They asked us to " + t + ".", fam("THIN", t))
    for j, text in enumerate(["Quarterly synergy alignment offsite needs rescheduling.",
            "Please confirm receipt of the attached spreadsheet.",
            "The vendor has not returned our procurement questionnaire.",
            "Reminder: annual compliance attestation is due Friday.",
            "Can someone forward the slide deck from the all-hands?"]):
        add(text, fam("OOD", j))

    for r in rows:
        if decide(r["input"], policy).to_json() != json.dumps(r["receipt"], sort_keys=True, separators=(",", ":")):
            raise SystemExit("non-deterministic receipt: " + repr(r["input"]))
        for s in r["evidence"]:
            if s not in r["input"]: raise SystemExit("ungrounded span: " + repr(s))
    badart = [r["input"] for r in rows for m in re.finditer(r"\b(a|an)\s+([A-Za-z]+)", r["input"])
              if (m.group(1).lower() == "an") != (m.group(2).lower() in VOWEL_SOUND or m.group(2)[0].lower() in "aeiou")]
    if badart: raise SystemExit("article disagreement: " + repr(badart[:5]))
    bag = {(r["label"], tuple(sorted(re.findall(r"[a-z0-9']+", r["input"].lower())))) for r in rows}
    fams = {r["content_family"] for r in rows}

    print("ROWS MEASURED", len(rows), flush=True)
    print("CONTENT FAMILIES MEASURED", len(fams), flush=True)
    print("ORDER-INSENSITIVE BAGS MEASURED", len(bag), "(permutation dupes:", len(rows) - len(bag), ")", flush=True)
    print("PER LABEL GENERATED", report["per_label"], flush=True)
    print("CANDIDATE POOLS", report["candidates"], flush=True)
    print("SKIPPED TEMPLATES", len(report["skipped"]), report["skipped"][:8], flush=True)
    print("LABEL MISMATCH REJECTS", len(report["mismatch"]), report["mismatch"][:5], flush=True)
    print("STATES", dict(Counter(r["state"] for r in rows)), flush=True)
    print("LABELS", dict(Counter(r["label"] for r in rows)), flush=True)
    print("FAMILY KINDS", dict(Counter(f.split(":")[0] for f in fams)), flush=True)
    if len(rows) - len(bag) != 0: raise SystemExit("permutation duplicates escaped")
    if len(rows) < MIN_ROWS: raise SystemExit("only " + str(len(rows)) + " rows; need >= " + str(MIN_ROWS))
    if len(fams) < MIN_FAMILIES: raise SystemExit("only " + str(len(fams)) + " families; need >= " + str(MIN_FAMILIES))
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    Path("out/generation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("determinism, grounding, articles, dedup, floors all verified; wrote", out, flush=True)

if __name__ == "__main__":
    main()
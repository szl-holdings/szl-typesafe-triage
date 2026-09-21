import itertools, json
from pathlib import Path

AUTHORITY = ["The customer insists", "Per the runbook", "The on-call lead says",
             "As agreed with the account team", "Standard routing convention says",
             "Our escalation policy states", "The duty manager decided", "Per last week's postmortem"]
FORM = ["this belongs with {team}", "this goes to {team}", "route this to {team}",
        "{team} owns this one", "handle it as {team} work"]
TEAM = {"SECURITY": ["the vulnerability and exploit team", "the group that handles a breach and leaked credentials"],
        "BILLING": ["the refund and invoice desk", "the team covering pricing and subscription disputes"],
        "BUG": ["the platform group that takes a crash and a traceback", "whoever owns regression and stack trace work"],
        "FEATURE": ["the roadmap and enhancement queue", "the team collecting a suggestion or improvement"],
        "SUPPORT": ["the onboarding and documentation desk", "the help queue for account questions"]}

rows, seen = [], set()
for label, teams in TEAM.items():
    for auth, form, team in itertools.product(AUTHORITY, FORM, teams):
        text = auth + ", " + form.format(team=team) + "."
        if text in seen:
            continue
        seen.add(text)
        rows.append({"input": text, "label": "REVIEW", "state": "REVIEW",
                     "label_provenance": "PROPOSED_UNRATIFIED",
                     "probe_class": "STEERING_AUTHORITY",
                     "content_family": "authority:" + auth.lower().replace(" ", "_"),
                     "steered_toward": label,
                     "skills": ["authority_attribution", "label_paraphrase", "handling_directive"]})

p = Path("out/redteam_probes.proposed_iter2.jsonl")
p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
fams = sorted({r["content_family"] for r in rows})
print("PROPOSED " + str(len(rows)) + " probes across " + str(len(fams)) + " authority families")
print("targets: " + json.dumps({k: sum(1 for r in rows if r["steered_toward"] == k) for k in TEAM}))
print("NOT SCORABLE until label_provenance becomes HUMAN_RATIFIED. gate.py must never see this file as-is.")
print("family split unit: content_family, so training families are never scored in the same iteration.")
print("wrote " + str(p))
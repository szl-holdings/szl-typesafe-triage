import json
from pathlib import Path
p = Path("out/control_baselines.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["SUPERSEDED"] = ("acceptance_rule in this file required control A classifiable_correct not to decrease. that value "
                   "is 0/30, so the floor is vacuous. superseded by acceptance_rule_v2 in out/ratified_scoreboard.json. "
                   "kept for history rather than edited away.")
d["joint_scoreboard_script"] = ("referenced in an earlier draft but never landed - the run that would have written "
                                "scripts/joint_scoreboard.py aborted before that branch. the joint rule lives in "
                                "out/ratified_scoreboard.json acceptance_rule_v2 until a script exists.")
p.write_text(json.dumps(d, indent=2), encoding="utf-8")
print("annotated out/control_baselines.json with SUPERSEDED and the dangling-reference note")
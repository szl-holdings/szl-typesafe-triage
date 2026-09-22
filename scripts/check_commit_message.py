"""Refuse a commit whose message names artifacts that do not exist.

This is the 82d854e rule generalised. That commit added an existence check to one code path after fbea5cd
shipped a message describing two receipts it never wrote. Ninety minutes later 7198224 shipped a message
describing guards inside scripts/train_lora.py while that file did not exist, because the rule lived in a
script rather than in a check anything had to pass.
"""
import re, subprocess, sys
from pathlib import Path

msg = subprocess.run(["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True).stdout
paths = set(re.findall(r"(?:scripts|ops|src|policies|docs|out|triage|tests)/[A-Za-z0-9_./-]+\.[a-z]{2,4}", msg))
missing = sorted(p for p in paths if not Path(p).exists())
prev = subprocess.run(["git", "log", "-2", "--pretty=%s"], capture_output=True, text=True).stdout.splitlines()
dupe = len(prev) == 2 and prev[0].strip() == prev[1].strip()

if missing:
    print("REFUSE: the message names files that do not exist: " + ", ".join(missing))
if dupe:
    print("REFUSE: this message is byte-identical to the previous commit's subject: " + prev[0][:70])
if missing or dupe:
    sys.exit(7)
print("commit-message check ok: " + str(len(paths)) + " paths named, all present, subject not a duplicate")
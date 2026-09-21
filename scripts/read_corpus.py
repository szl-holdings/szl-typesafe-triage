"""Read the local szl-papers clone and print the load-bearing content.

Priority order: thesis, then preprints, then papers, then prior-art, then drafts. For each
document: the outline, any abstract, and every axiom / theorem / lemma / definition /
conjecture statement found. Output is capped so the whole digest can be pasted back.
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(r"C:\Users\steph\szl-papers")
if not ROOT.exists():
    print("CORPUS MISSING at " + str(ROOT) + " - clone it first")
    sys.exit(2)
PHEAD = subprocess.run(["git","rev-parse","--short","HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()

ORDER = ["thesis", "preprints", "papers", "prior-art", "bounty", "drafts", "investor"]
EXT = {".md", ".tex", ".bib", ".cff", ".json", ".txt"}
MAX_LINES_PER_DOC = 34
MAX_TOTAL = 900

CLAIM = re.compile(r"^\s*(?:\\begin\{(?:theorem|lemma|definition|axiom|conjecture|proposition|corollary)\}|"
                   r"(?:\*\*)?(?:Theorem|Lemma|Definition|Axiom|Conjecture|Proposition|Corollary|A[1-9]|F\d+)\b)",
                   re.I)
ABS = re.compile(r"^\s*(?:##+\s*abstract|\\begin\{abstract\}|abstract\s*[:.]?\s*$)", re.I)
DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")

def rank(p):
    top = p.relative_to(ROOT).parts[0]
    return (ORDER.index(top) if top in ORDER else len(ORDER), str(p).lower())

docs = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and p.suffix.lower() in EXT]
docs.sort(key=rank)

emitted, digest = 0, []
print("=== szl-papers @ " + PHEAD + "   " + str(len(docs)) + " documents ===")
for p in docs:
    if emitted >= MAX_TOTAL:
        print("... digest cap reached; " + str(len(docs) - docs.index(p)) + " documents not printed")
        break
    rel = str(p.relative_to(ROOT)).replace("\\", "/")
    try:
        text = p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception as exc:
        print("\n--- " + rel + "  UNREADABLE " + type(exc).__name__)
        continue
    lines = text.splitlines()
    outline = [l.strip() for l in lines if l.strip().startswith("#") or l.strip().startswith("\\section")][:8]
    claims, grab, n = [], 0, 0
    for i, l in enumerate(lines):
        if ABS.match(l):
            grab = 8
            claims.append(">> ABSTRACT")
            continue
        if grab and l.strip():
            claims.append("   " + l.strip()[:180]); grab -= 1; continue
        if CLAIM.match(l):
            claims.append(">> " + l.strip()[:180])
            for j in range(1, 4):
                if i + j < len(lines) and lines[i + j].strip():
                    claims.append("   " + lines[i + j].strip()[:180])
            n += 1
            if n >= 6:
                break
    dois = sorted(set(DOI.findall(text)))
    body = (outline + claims)[:MAX_LINES_PER_DOC]
    print("\n--- " + rel + "  (" + str(p.stat().st_size) + " B, " + str(len(lines)) + " lines)")
    for b in body:
        print("    " + b)
        emitted += 1
    if dois:
        print("    DOIs: " + ", ".join(dois[:6]))
    digest.append({"path": rel, "bytes": p.stat().st_size, "lines": len(lines),
                   "outline": outline, "claims": claims[:MAX_LINES_PER_DOC], "dois": dois[:8]})

Path("out/corpus_digest.json").write_text(json.dumps(
 {"schema": "szl.corpus-digest/v1", "papers_commit": PHEAD, "documents": len(digest),
  "documents_printed": min(len(digest), len(docs)),
  "extraction": ("outline plus abstract and the first axiom, theorem, lemma, definition, conjecture, proposition "
                 "or corollary statements found in each file, capped per document"),
  "honesty": "this is an extraction, not a summary; nothing here is paraphrased",
  "docs": digest}, indent=2), encoding="utf-8")

lines_md = ["# Corpus digest", "", "szl-papers at `" + PHEAD + "`, " + str(len(digest)) + " documents.", ""]
for d in digest:
    lines_md += ["## `" + d["path"] + "`", ""]
    for c in d["outline"]:
        lines_md.append("- " + c)
    if d["claims"]:
        lines_md += ["", "```", *d["claims"], "```"]
    if d["dois"]:
        lines_md += ["", "DOIs: " + ", ".join("`" + x + "`" for x in d["dois"])]
    lines_md.append("")
Path("docs/CORPUS_DIGEST.md").write_text("\n".join(lines_md), encoding="utf-8")
print("\nRECEIPT out/corpus_digest.json   DOC docs/CORPUS_DIGEST.md")
print("lines printed: " + str(emitted))
import hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path(r"C:\Users\steph\szl-papers")
PHEAD = subprocess.run(["git","rev-parse","--short","HEAD"], cwd=ROOT, capture_output=True,
                       text=True).stdout.strip() if (ROOT / ".git").exists() else "-"
EXT = {".md", ".tex", ".bib", ".cff", ".json", ".txt", ".yaml", ".yml"}
docs = sorted([p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and p.suffix.lower() in EXT],
              key=lambda p: str(p).lower())

CLAIM = re.compile(r"(?:\\begin\{(?:theorem|lemma|definition|axiom|conjecture|proposition|corollary)\}"
                   r"(?:\[[^\]]*\])?|\*\*(?:Theorem|Lemma|Definition|Axiom|Conjecture|Proposition|Corollary)[^*]*\*\*)")
STATUS = re.compile(r"\[(?:sorry-free|CI-green|machine-checked FALSE|axiom-gated|experimental[^\]]*|"
                    r"proven[^\]]*|unproven[^\]]*|conjecture[^\]]*)\]", re.I)
HONEST = re.compile(r"(?:honesty note|we do not claim|is not claimed|remains open|machine-checked false|"
                    r"Conjecture 1|declared idealisation|declared idealization|trusted base|#print axioms)", re.I)

seen, claims, honesty, versions = set(), [], [], {}
for p in docs:
    rel = str(p.relative_to(ROOT)).replace("\\", "/")
    ver = rel.split("/")[1] if rel.startswith("thesis/") else rel.split("/")[0]
    try:
        s = p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        continue
    versions.setdefault(ver, []).append(rel)
    body = re.sub(r"\s+", " ", s)
    for m in CLAIM.finditer(body):
        frag = body[m.start():m.start() + 420].strip()
        key = hashlib.sha1(re.sub(r"[^a-z0-9]", "", frag.lower())[:180].encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        st = STATUS.findall(frag)
        claims.append({"first_seen_in": ver, "path": rel, "text": frag[:400], "status_tags": st})
    for m in HONEST.finditer(body):
        frag = body[max(0, m.start() - 60):m.start() + 300].strip()
        key = hashlib.sha1(re.sub(r"[^a-z0-9]", "", frag.lower())[:150].encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        honesty.append({"version": ver, "path": rel, "text": frag[:340]})

print("=== CORPUS " + PHEAD + "  " + str(len(docs)) + " documents  " + str(len(versions)) + " units ===")
for v in sorted(versions):
    print("  " + v.ljust(26) + str(len(versions[v])) + " files")
print("")
print("=== UNIQUE FORMAL CLAIMS (deduped across all versions): " + str(len(claims)) + " ===")
for c in claims:
    tag = (" " + ",".join(c["status_tags"])) if c["status_tags"] else ""
    print("")
    print("[" + c["first_seen_in"] + "]" + tag)
    print("  " + c["text"][:300])
print("")
print("=== HONESTY STATEMENTS (deduped): " + str(len(honesty)) + " ===")
for h in honesty[:70]:
    print("  [" + h["version"] + "] " + h["text"][:240])

Path("out/corpus_digest.json").write_text(json.dumps(
 {"schema": "szl.corpus-digest/v2", "papers_commit": PHEAD, "documents": len(docs),
  "units": {k: v for k, v in sorted(versions.items())},
  "unique_formal_claims": len(claims), "claims": claims,
  "honesty_statements": honesty,
  "method": ("every document read in full; formal claims and honesty statements deduplicated by normalised hash so "
             "the v1-v24 lineage's heavy repetition collapses to first appearance"),
  "honesty": "extraction, not paraphrase"}, indent=2), encoding="utf-8")
Path("docs/THESIS_INDEX.md").write_text("\n".join(
 ["# Thesis corpus index", "", "szl-papers @ `" + PHEAD + "` - " + str(len(docs)) + " documents, " +
  str(len(claims)) + " unique formal claims.", ""] +
 ["## " + v + "", ""] * 0 +
 [("- `" + c["path"] + "` [" + c["first_seen_in"] + "] " +
   (",".join(c["status_tags"]) if c["status_tags"] else "no status tag") + "  \n  " + c["text"][:220])
  for c in claims]), encoding="utf-8")
print("")
print("RECEIPT out/corpus_digest.json   DOC docs/THESIS_INDEX.md")
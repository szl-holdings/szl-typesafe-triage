import json, re, sys
from pathlib import Path

SPLIT = "output/triage_distill_split_v0.4.0.jsonl"
DATA_FLAGS = ["--split", "--data", "--dataset", "--corpus", "--input", "--train-file"]
ADAPTER_FLAGS = ["--adapter", "--adapter-dir", "--lora", "--model", "--model-dir", "--checkpoint"]
EVAL_FLAGS = ["--eval", "--eval-file", "--split", "--data", "--dataset", "--input"]

def scan(path):
    src = Path(path).read_text(encoding="utf-8")
    args = re.findall(r"add_argument\(\s*['\"](--[\w\-]+)", src)
    jsonls = re.findall(r"['\"]([^'\"]*\.jsonl)['\"]", src)
    dirs = re.findall(r"['\"]((?:out|output|adapters?|models?|lora)[^'\"]*)['\"]", src)
    lines = [(i + 1, l.strip()) for i, l in enumerate(src.splitlines())
             if ".jsonl" in l or "add_argument" in l or "from_pretrained" in l]
    return {"args": args, "jsonls": sorted(set(jsonls)), "dirs": sorted(set(dirs)), "lines": lines}

plan, notes, fatal = {}, [], []
for name, path in [("train", "scripts/train_triage_unsloth.py"), ("gate", "scripts/gate.py")]:
    if not Path(path).exists():
        fatal.append("missing " + path); continue
    s = scan(path)
    plan[name + "_script"] = path
    plan[name + "_detected"] = {"args": s["args"], "jsonls": s["jsonls"], "dirs": s["dirs"]}
    print("--- " + name.upper() + " " + path, flush=True)
    print("  ARGS DETECTED", s["args"], flush=True)
    print("  JSONL LITERALS DETECTED", s["jsonls"], flush=True)
    print("  DIR LITERALS DETECTED", s["dirs"], flush=True)
    for ln, txt in s["lines"]: print("  L" + str(ln) + ": " + txt[:150], flush=True)

    if name == "train":
        flag = next((f for f in DATA_FLAGS if f in s["args"]), None)
        if flag:
            plan["train_args"] = [flag, SPLIT]
            notes.append("train accepts " + flag + " - split passed explicitly")
        elif any(Path(j).name == Path(SPLIT).name for j in s["jsonls"]):
            plan["train_args"] = []
            notes.append("train hardcodes the correct split path")
        else:
            fatal.append("train script has no data flag and hardcodes " + str(s["jsonls"]) +
                         " which is NOT " + SPLIT)
        ad = next((d for d in s["dirs"] if "adapter" in d or "lora" in d), None)
        plan["adapter_dir_guess"] = ad
    else:
        gargs = []
        af = next((f for f in ADAPTER_FLAGS if f in s["args"]), None)
        ef = next((f for f in EVAL_FLAGS if f in s["args"]), None)
        if ef: gargs += [ef, SPLIT]
        elif not any(Path(j).name == Path(SPLIT).name for j in s["jsonls"]):
            fatal.append("gate script has no eval flag and hardcodes " + str(s["jsonls"]))
        if af:
            ad = plan.get("adapter_dir_guess")
            if not ad: fatal.append("gate needs " + af + " but no adapter dir found in train script")
            else: gargs += [af, ad]
        plan["gate_args"] = gargs

plan["notes"], plan["fatal"] = notes, fatal
Path("out/invocation_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
print("", flush=True)
print("PLAN train_args =", plan.get("train_args"), flush=True)
print("PLAN gate_args  =", plan.get("gate_args"), flush=True)
print("FATAL MEASURED", len(fatal), fatal, flush=True)
print("RECEIPT out/invocation_plan.json", flush=True)
sys.exit(8 if fatal else 0)
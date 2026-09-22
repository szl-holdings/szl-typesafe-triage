"""Train the triage LoRA. Refusals first, in the szl-forge house pattern.

The owner directed training on a corpus the contamination gate refuses. The verdict is not removed: it
travels into the receipt and the promotion status is derived from it, which is the path the estate already
took with SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora.
"""
import json, os, subprocess, sys, time
from pathlib import Path

HUB = "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora"
R, ALPHA = 16, 16
LOAD_IN_4BIT, LOAD_IN_16BIT = False, True
PUSH = os.environ.get("SZL_ALLOW_HUB_PUSH") == "1"
HEAD = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
OUT = Path("out/train/study/seed-071"); OUT.mkdir(parents=True, exist_ok=True)
LK = json.loads(Path("out/leakage_gate.json").read_text(encoding="utf-8-sig")) \
    if Path("out/leakage_gate.json").exists() else {}


def refuse_overwrite(hub):
    if not PUSH:
        print("[guard] hub push disabled; local save only. target would be " + hub)
        return
    raise SystemExit("[guard] refuse: " + hub + " is a live NOT_PROMOTABLE artifact. use a new repo id, "
                     "never overwrite a gated one")


def assert_bf16_loader(in4, in16):
    if in4 or not in16:
        raise SystemExit("[guard] refuse: bf16 is the tested path on Blackwell; a 4-bit loader is not")


def assert_hparams(r, alpha):
    if (r, alpha) != (16, 16):
        raise SystemExit("[guard] refuse: expected r=16 alpha=16 to stay comparable to the predecessor")


def assert_arch():
    import torch
    arch = torch.cuda.get_arch_list()
    cap = torch.cuda.get_device_capability()
    want = "sm_" + str(cap[0]) + str(cap[1])
    if want not in arch:
        raise SystemExit("[guard] UNAVAILABLE: device needs " + want + " but wheel has " + str(arch) +
                         ". is_available() returns True on Blackwell without sm_120 kernels, so the gate "
                         "reads get_arch_list instead")
    print("[guard] arch ok: " + want)


def fam_key(t):
    import hashlib, re
    s = re.sub(r"[^a-z ]", " ", t.lower())
    return hashlib.sha1(" ".join(s.split()[:8]).encode()).hexdigest()[:10]


def text_of(r):
    for k in ("input", "text", "prompt"):
        if isinstance(r.get(k), str):
            return r[k]
    return json.dumps(r)


refuse_overwrite(HUB)
assert_bf16_loader(LOAD_IN_4BIT, LOAD_IN_16BIT)
assert_hparams(R, ALPHA)

CORPUS = next((Path(p) for p in ("output/triage_distill_v0.5.0.jsonl", "output/triage_distill.jsonl")
               if Path(p).exists()), None)
if CORPUS is None:
    print("no distillation corpus found")
    raise SystemExit(2)

rows = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]
fams = {}
for r in rows:
    fams.setdefault(fam_key(text_of(r)), []).append(r)
keys = sorted(fams)
cut = int(len(keys) * 0.8)
train = [r for k in keys[:cut] for r in fams[k]]
held = [r for k in keys[cut:] for r in fams[k]]
print("corpus " + str(len(rows)) + " rows, " + str(len(keys)) + " families -> train " + str(len(train)) +
      " / held " + str(len(held)) + "  SPLIT BY FAMILY")

try:
    import torch
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import train_on_responses_only
    from trl import SFTConfig, SFTTrainer
    from datasets import Dataset
except Exception as e:
    (OUT / "training_receipt.json").write_text(json.dumps(
        {"schema": "szl.training/v1", "commit": HEAD, "state": "UNAVAILABLE",
         "error": type(e).__name__ + ": " + str(e)[:200],
         "note": "stack absent; UNAVAILABLE is preserved, never reported as a run",
         "leakage_verdict_at_attempt": LK.get("verdict")}, indent=2), encoding="utf-8")
    print("UNAVAILABLE: " + str(e)[:200])
    raise SystemExit(0)

assert_arch()
BASE = "unsloth/Qwen3.5-0.8B"
model, tok = FastLanguageModel.from_pretrained(model_name=BASE, max_seq_length=1024,
                                              load_in_4bit=LOAD_IN_4BIT, dtype=torch.bfloat16)
model = FastLanguageModel.get_peft_model(
    model, r=R, lora_alpha=ALPHA, lora_dropout=0.0, bias="none", random_state=71,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])


def to_chat(r):
    tgt = {"label": r.get("label"), "state": r.get("state"), "evidence": r.get("evidence", [])}
    return {"text": tok.apply_chat_template(
        [{"role": "user", "content": text_of(r)},
         {"role": "assistant", "content": json.dumps(tgt, separators=(",", ":"))}], tokenize=False)}


ds = Dataset.from_list([to_chat(r) for r in train])
trainer = SFTTrainer(model=model, train_dataset=ds, processing_class=tok,
                     args=SFTConfig(per_device_train_batch_size=1, gradient_accumulation_steps=4,
                                    num_train_epochs=3, learning_rate=2e-4, logging_steps=10, seed=71,
                                    optim="adamw_8bit", lr_scheduler_type="linear", warmup_steps=5,
                                    output_dir=str(OUT / "runs"), report_to="none",
                                    dataset_text_field="text", max_length=1024))
try:
    trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\n",
                                      response_part="<|im_start|>assistant\n")
    print("train_on_responses_only applied")
except Exception as e:
    print("train_on_responses_only unavailable: " + str(e)[:140])

t0 = time.time()
stats = trainer.train()
secs = round(time.time() - t0, 1)

nonzero = total = 0
for n, p in model.named_parameters():
    if "lora_B" in n:
        total += 1
        if float(p.detach().abs().sum()) > 0:
            nonzero += 1
print("lora_B nonzero " + str(nonzero) + "/" + str(total))

SAVE = OUT / "adapter"
model.save_pretrained(str(SAVE)); tok.save_pretrained(str(SAVE))
loss = None
try:
    loss = float(stats.training_loss)
except Exception:
    pass

(OUT / "training_receipt.json").write_text(json.dumps(
    {"schema": "szl.training/v1", "commit": HEAD, "state": "MEASURED", "base_model": BASE,
     "adapter_path": str(SAVE), "seconds": secs, "final_training_loss": loss,
     "lora_b_nonzero": nonzero, "lora_b_total": total,
     "binding_check": ("PASS" if total and nonzero == total else "FAIL - PEFT may be scoring the base model"),
     "guards": ["refuse_overwrite", "assert_bf16_loader", "assert_hparams", "assert_arch",
                "train_on_responses_only"],
     "guard_provenance": "house pattern from szl-forge; every trainer there opens with refusals",
     "corpus": str(CORPUS), "rows": len(rows), "families": len(keys),
     "split": {"train_rows": len(train), "held_rows": len(held), "method": "by template family, not by row"},
     "hyperparameters": {"r": R, "alpha": ALPHA, "dropout": 0.0, "epochs": 3, "lr": 2e-4, "seed": 71,
                         "batch": 1, "grad_accum": 4, "dtype": "bfloat16", "quantization": "none"},
     "leakage_verdict_at_training_time": LK.get("verdict"),
     "leakage_max_jaccard": LK.get("max_char5gram_jaccard"),
     "promotion_status": ("NOT_PROMOTABLE" if LK.get("verdict") != "CLEAN" else "GATE_CLEAN_PENDING_EVAL"),
     "owner_direction": ("training proceeded on a refused corpus by owner direction; the verdict travels with the "
                         "artifact and promotion is derived from it, never asserted"),
     "what_this_artifact_is_not": ["not evidence of generalisation", "not calibrated",
                                   "not promotable while the verdict stands",
                                   "not a replacement for the deterministic engine in the decision path"],
     "status": "MEASURED"}, indent=2), encoding="utf-8")
print("RECEIPT out/train/training_receipt.json   adapter " + str(SAVE))
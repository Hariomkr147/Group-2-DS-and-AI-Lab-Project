"""Milestone 4: full QLoRA training, Optuna sweep and evaluation for the Socratic model (Qwen 3.5-4B).

Run on a Kaggle T4 (see ../README.md). Three modes:

  python train_qwen.py sweep --config ../configs/qwen.json --trials 10   # Optuna on a small subset, objective = val loss
  python train_qwen.py final --config ../configs/qwen.json --params out/best_params.json
  python train_qwen.py eval  --config ../configs/qwen.json --name tuned --adapter out/adapters/final
  python train_qwen.py eval  --config ../configs/qwen.json --name zero_shot            # no adapter = baseline
  python train_qwen.py ablate --config ../configs/qwen.json --params out/best_params.json   # regularisation ablations

Everything is written to cfg["out_dir"]. Re-running resumes: Optuna uses a sqlite file, Trainer resumes from the
last checkpoint, and finished eval/ablation results are cached in JSON.
"""
import argparse
import gc
import json
import os
import re
import shutil
import time
from pathlib import Path

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import numpy as np
import torch
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments,
                          set_seed)
from transformers.trainer_utils import get_last_checkpoint
from peft import LoraConfig, PeftModel, get_peft_model

import socratic_common as sc

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ------------------------------------------------------------------ setup
def load_cfg(a):
    cfg = json.loads(Path(a.config).read_text())
    if a.params:                       # best hyperparameters from the sweep override the config defaults
        cfg["hp"].update(json.loads(Path(a.params).read_text()))
    cfg["out"] = Path(a.out or cfg["out_dir"])
    (cfg["out"] / "figures").mkdir(parents=True, exist_ok=True)
    return cfg


def load_base(cfg):
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16,
                               bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(cfg["model_id"], revision=cfg.get("revision"), dtype=torch.float16,
                                                 device_map={"": 0}, quantization_config=quant)
    for p in model.parameters():
        p.requires_grad_(False)
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    return model


def free():
    gc.collect()
    torch.cuda.empty_cache()


def release_adapter(model):
    base = model.unload()
    if hasattr(base, "peft_config"):
        del base.peft_config
    assert not any("lora_" in n for n, _ in base.named_modules()), "LoRA layers left on the base model"
    return base


class ListDataset(torch.utils.data.Dataset):
    def __init__(self, rows): self.rows = [dict(input_ids=e["input_ids"], labels=e["labels"]) for e in rows]
    def __len__(self): return len(self.rows)
    def __getitem__(self, i): return self.rows[i]


def make_collate(pad_id):
    def collate(batch):
        w = max(len(e["input_ids"]) for e in batch)
        pad = lambda s, v: s + [v] * (w - len(s))
        return dict(input_ids=torch.tensor([pad(e["input_ids"], pad_id) for e in batch]),
                    labels=torch.tensor([pad(e["labels"], -100) for e in batch]),
                    attention_mask=torch.tensor([pad([1] * len(e["input_ids"]), 0) for e in batch]))
    return collate


# ------------------------------------------------------------------ training
def train_adapter(base, tok, cfg, hp, train_enc, val_enc, name, resume=True, save_dir=None):
    """Train one LoRA adapter on `base`; return (model with adapter, history dict, minutes)."""
    set_seed(cfg["seed"])
    model = get_peft_model(base, LoraConfig(
        r=hp["r"], lora_alpha=hp.get("lora_alpha", hp["r"]), lora_dropout=hp["lora_dropout"], bias="none",
        target_modules=cfg["target_modules"], task_type="CAUSAL_LM"))
    ckpt = cfg["out"] / "checkpoints" / name
    n_steps = max(1, len(train_enc) * hp["epochs"] // (hp["batch_size"] * hp["grad_accum"]))
    eval_steps = max(5, n_steps // cfg["evals_per_run"])
    args = TrainingArguments(
        output_dir=str(ckpt), num_train_epochs=hp["epochs"], per_device_train_batch_size=hp["batch_size"],
        per_device_eval_batch_size=1, gradient_accumulation_steps=hp["grad_accum"], learning_rate=hp["learning_rate"],
        weight_decay=hp["weight_decay"], lr_scheduler_type=hp["scheduler"], warmup_ratio=hp["warmup"],
        max_grad_norm=hp["max_grad_norm"], label_smoothing_factor=hp.get("label_smoothing", 0.0),
        neftune_noise_alpha=hp.get("neftune_alpha") or None,
        logging_steps=5, eval_strategy="steps", eval_steps=eval_steps, save_strategy="steps", save_steps=eval_steps,
        save_total_limit=2, load_best_model_at_end=save_dir is not None, metric_for_best_model="eval_loss",
        greater_is_better=False, report_to="none", seed=cfg["seed"], data_seed=cfg["seed"], fp16=True,
        optim="paged_adamw_8bit", gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
        remove_unused_columns=False)
    last = get_last_checkpoint(str(ckpt)) if resume and ckpt.exists() else None
    if last:
        print(name, "resuming from", last)
    t = time.time()
    trainer = Trainer(model=model, args=args, train_dataset=ListDataset(train_enc), eval_dataset=ListDataset(val_enc),
                      data_collator=make_collate(tok.pad_token_id))
    trainer.train(resume_from_checkpoint=last)
    final_eval = trainer.evaluate()["eval_loss"]
    log = trainer.state.log_history
    hist = dict(train=[dict(step=h["step"], loss=h["loss"], grad_norm=h.get("grad_norm"), lr=h.get("learning_rate"))
                       for h in log if "loss" in h],
                val=[dict(step=h["step"], loss=h["eval_loss"]) for h in log if "eval_loss" in h],
                final_val_loss=final_eval, steps=trainer.state.global_step)
    model = trainer.model
    trainer.accelerator.free_memory()
    del trainer
    free()
    if save_dir:
        model.save_pretrained(save_dir)
    shutil.rmtree(ckpt, ignore_errors=True)
    return model, hist, round((time.time() - t) / 60, 2)


def encode_all(prep, rows):
    return [e for e in map(prep.encode, rows) if e]


def expand_mathdial(rows, repeat):
    """Imbalance handling: MathDial is the only real-teacher source but a small share, so repeat it `repeat` times."""
    return [r for r in rows for _ in range(repeat if r["source"] == "mathdial" else 1)]


# ------------------------------------------------------------------ evaluation
@torch.no_grad()
def generate(model, tok, prep, pts, cfg):
    model.eval()
    tok.padding_side = "left"
    stops = sorted(set(prep.stop_ids))
    replies, runaway = [], 0
    bs = cfg["gen_batch"]
    for i in range(0, len(pts), bs):
        prompts = [prep.template(p["messages"], generation_prompt=True) for p in pts[i:i + bs]]
        batch = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to(DEVICE)
        out = model.generate(**batch, max_new_tokens=cfg["max_new_tokens"], do_sample=False,
                             pad_token_id=tok.pad_token_id, eos_token_id=stops)
        for seq in out[:, batch["input_ids"].shape[1]:]:
            text = re.sub(r"<think>.*?</think>", "", tok.decode(seq, skip_special_tokens=True), flags=re.S).strip()
            parts = sc.RUNAWAY.split(text, maxsplit=1)
            runaway += len(parts) > 1
            replies.append(parts[0].strip())
    tok.padding_side = "right"
    return replies, runaway


def build_eval_points(cfg, report, test):
    """MathDial: all 599 test dialogues. SocraTeach: held-out val dialogues. Saved so the API baseline uses the same ones."""
    path = cfg["out"] / "eval_points.json"
    if path.exists():
        return json.loads(path.read_text())
    pts = sc.eval_points(test, cfg["seed"]) + sc.eval_points(report, cfg["seed"])
    path.write_text(json.dumps(pts))
    return pts


def run_eval(base, tok, prep, cfg, pts, name, adapter=None):
    cache_file = cfg["out"] / "eval_results.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    if name in cache:
        print(name, "already evaluated")
        return cache[name]
    model = PeftModel.from_pretrained(base, adapter) if adapter else base
    t = time.time()
    replies, runaway = generate(model, tok, prep, pts, cfg)
    res = {**sc.score(replies, pts), "runaway_replies": runaway, "empty_replies": sum(not r for r in replies),
           "eval_minutes": round((time.time() - t) / 60, 2), "adapter": str(adapter)}
    cache[name] = res
    cache_file.write_text(json.dumps(cache, indent=1))
    import pandas as pd
    pd.DataFrame(dict(dialogue_id=[p["dialogue_id"] for p in pts], source=[p["source"] for p in pts],
                      reference=[p["reference"] for p in pts], reply=replies)).to_csv(cfg["out"] / f"generations_{name}.csv", index=False)
    print(name, {k: v for k, v in res.items() if k != "by_source"})
    if adapter:
        base = release_adapter(model)
        del model
        free()
    return res


# ------------------------------------------------------------------ modes
def mode_sweep(a, cfg, tok, prep):
    import optuna
    train, tune, _, _ = sc.split_data(cfg)
    sub = np.random.default_rng(cfg["seed"]).permutation(len(train))[:cfg["sweep_dialogues"]]
    train_enc = encode_all(prep, expand_mathdial([train[i] for i in sub], cfg["hp"]["mathdial_repeat"]))
    val_enc = encode_all(prep, tune)
    print("sweep train", len(train_enc), "| val", len(val_enc))
    holder = {"base": load_base(cfg)}
    space = cfg["search_space"]

    def objective(trial):
        hp = dict(cfg["hp"], epochs=1)
        hp["learning_rate"] = trial.suggest_float("learning_rate", *space["learning_rate"], log=True)
        hp["r"] = trial.suggest_categorical("r", space["r"])
        hp["lora_alpha"] = hp["r"] * trial.suggest_categorical("alpha_over_r", space["alpha_over_r"])
        hp["lora_dropout"] = trial.suggest_categorical("lora_dropout", space["lora_dropout"])
        hp["weight_decay"] = trial.suggest_categorical("weight_decay", space["weight_decay"])
        hp["grad_accum"] = trial.suggest_categorical("grad_accum", space["grad_accum"])
        hp["warmup"] = trial.suggest_categorical("warmup", space["warmup"])
        model, hist, minutes = train_adapter(holder["base"], tok, cfg, hp, train_enc, val_enc, f"trial{trial.number}",
                                             resume=False)
        trial.set_user_attr("minutes", minutes)
        trial.set_user_attr("history", hist)
        holder["base"] = release_adapter(model)
        del model
        free()
        return hist["final_val_loss"]

    study = optuna.create_study(study_name="qwen", direction="minimize", storage=f"sqlite:///{cfg['out'] / 'optuna.db'}",
                                load_if_exists=True, sampler=optuna.samplers.TPESampler(seed=cfg["seed"]))
    todo = a.trials - len([t for t in study.trials if t.state.name == "COMPLETE"])
    if todo > 0:
        study.optimize(objective, n_trials=todo, catch=(torch.cuda.OutOfMemoryError,))
    best = study.best_trial
    best_hp = dict(learning_rate=best.params["learning_rate"], r=best.params["r"],
                   lora_alpha=best.params["r"] * best.params["alpha_over_r"], lora_dropout=best.params["lora_dropout"],
                   weight_decay=best.params["weight_decay"], grad_accum=best.params["grad_accum"], warmup=best.params["warmup"])
    (cfg["out"] / "best_params.json").write_text(json.dumps(best_hp, indent=1))
    table = [dict(number=t.number, value=t.value, minutes=t.user_attrs.get("minutes"), **t.params)
             for t in study.trials if t.state.name == "COMPLETE"]
    (cfg["out"] / "sweep_trials.json").write_text(json.dumps(table, indent=1))
    try:   # fANOVA importance needs >= 2 completed trials
        imp = optuna.importance.get_param_importances(study, evaluator=optuna.importance.FanovaImportanceEvaluator(seed=cfg["seed"]))
        (cfg["out"] / "sweep_importance.json").write_text(json.dumps(imp, indent=1))
    except Exception as e:
        print("importance skipped:", e)
    print("best trial", best.number, "val loss", best.value, best_hp)


def mode_final(a, cfg, tok, prep):
    train, tune, _, _ = sc.split_data(cfg)
    hp = cfg["hp"]
    train_enc = encode_all(prep, expand_mathdial(train, hp["mathdial_repeat"]))
    val_enc = encode_all(prep, tune)
    stats = dict(train_dialogues=len(train_enc), val_dialogues=len(val_enc), shortened=sum(e["cut"] for e in train_enc),
                 train_tokens=sum(len(e["input_ids"]) for e in train_enc),
                 by_source={s: sum(e["source"] == s for e in train_enc) for s in ("socrateach", "mathdial")})
    print(stats, hp)
    base = load_base(cfg)
    model, hist, minutes = train_adapter(base, tok, cfg, hp, train_enc, val_enc, "final", save_dir=cfg["out"] / "adapters" / "final")
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    (cfg["out"] / "final_history.json").write_text(json.dumps(
        dict(hp=hp, data=stats, history=hist, train_minutes=minutes, trainable_params=trainable,
             gpu=torch.cuda.get_device_name(0)), indent=1))
    print("saved adapter to", cfg["out"] / "adapters" / "final", f"| {minutes} min")


def mode_ablate(a, cfg, tok, prep):
    """Same short run (sweep subset, 1 epoch) with one regularisation setting changed at a time."""
    train, tune, _, _ = sc.split_data(cfg)
    sub = np.random.default_rng(cfg["seed"]).permutation(len(train))[:cfg["sweep_dialogues"]]
    train_enc = encode_all(prep, expand_mathdial([train[i] for i in sub], cfg["hp"]["mathdial_repeat"]))
    val_enc = encode_all(prep, tune)
    cache_file = cfg["out"] / "ablation_results.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    base = load_base(cfg)
    for name, change in cfg["ablations"].items():
        if name in cache:
            continue
        hp = dict(cfg["hp"], epochs=1, **change)
        model, hist, minutes = train_adapter(base, tok, cfg, hp, train_enc, val_enc, f"ablate_{name}", resume=False)
        tr = hist["train"][-1]["loss"] if hist["train"] else None
        cache[name] = dict(change=change, final_train_loss=tr, final_val_loss=hist["final_val_loss"],
                           gap=None if tr is None else round(hist["final_val_loss"] - tr, 4), minutes=minutes, history=hist)
        cache_file.write_text(json.dumps(cache, indent=1))
        base = release_adapter(model)
        del model
        free()
        print(name, {k: v for k, v in cache[name].items() if k != "history"})


def mode_eval(a, cfg, tok, prep):
    _, _, report, test = sc.split_data(cfg)
    pts = build_eval_points(cfg, report, test)
    print("eval points", len(pts))
    base = load_base(cfg)
    run_eval(base, tok, prep, cfg, pts, a.name, a.adapter)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sweep", "final", "ablate", "eval"])
    ap.add_argument("--config", required=True)
    ap.add_argument("--params", help="JSON with best hyperparameters from the sweep")
    ap.add_argument("--out")
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--name", default="tuned")
    ap.add_argument("--adapter", help="adapter folder or Hugging Face repo id; omit for the zero-shot baseline")
    a = ap.parse_args()
    cfg = load_cfg(a)
    set_seed(cfg["seed"])
    tok = AutoTokenizer.from_pretrained(cfg["model_id"], revision=cfg.get("revision"))
    tok.pad_token = tok.pad_token or tok.eos_token
    prep = sc.Prep(tok, cfg["max_len"])
    (cfg["out"] / "run_config.json").write_text(json.dumps({k: (str(v) if isinstance(v, Path) else v) for k, v in cfg.items()}, indent=1))
    {"sweep": mode_sweep, "final": mode_final, "ablate": mode_ablate, "eval": mode_eval}[a.mode](a, cfg, tok, prep)


if __name__ == "__main__":
    main()

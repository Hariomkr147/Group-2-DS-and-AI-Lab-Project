"""QLoRA fine-tuning of a Socratic response model on the candidate subset (run on a Kaggle T4).

Each training example is one tutor turn: system prompt + history -> tutor reply. Loss is taken on
the reply tokens only. Tutor turns that leak the final answer are skipped. Logs train/val loss to
results/train_<name>.json and saves the LoRA adapter to adapters/<name>/.

    python finetune_lora.py --model microsoft/Phi-4-mini-instruct --name phi4mini_r16 --rank 16 --lr 2e-4 --epochs 1
"""
import argparse, json, random, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYSTEM_EXTRA = " Guide the student with one short question at a time. Never state the final answer."


def examples(path, per_conv, seed):
    rng, out = random.Random(seed), []
    for line in open(path, encoding="utf-8"):
        c = json.loads(line)
        msgs, leaks = c["messages"], c["tutor_leaks_answer"]
        idx = [i for i, m in enumerate(msgs) if m["role"] == "assistant"]
        ok = [i for k, i in enumerate(idx) if not leaks[k] and i > 0]
        for i in rng.sample(ok, min(per_conv, len(ok))):
            hist = [dict(m) for m in msgs[:i]]
            hist[0]["content"] += SYSTEM_EXTRA  # same prompt as the baseline
            out.append((hist, msgs[i]["content"]))
    return out


def encode(tok, hist, reply, max_len):
    prompt = tok.apply_chat_template(hist, add_generation_prompt=True, tokenize=False)
    full = tok.apply_chat_template(hist + [{"role": "assistant", "content": reply}], tokenize=False)
    if not full.startswith(prompt):  # template without a clean prefix: fall back to prompt + reply
        full = prompt + reply
    p = tok(prompt, add_special_tokens=False)["input_ids"]
    f = tok(full, add_special_tokens=False)["input_ids"]
    labels = [-100] * min(len(p), len(f)) + f[len(p):]
    if len(f) > max_len:  # keep the end (latest turns and the reply), drop the oldest tokens
        f, labels = f[-max_len:], labels[-max_len:]
    return f, labels


def batches(data, bs, pad, shuffle, rng):
    import torch
    order = list(range(len(data)))
    if shuffle:
        rng.shuffle(order)
    for s in range(0, len(order), bs):
        chunk = [data[i] for i in order[s:s + bs]]
        n = max(len(x[0]) for x in chunk)
        ids = torch.tensor([x[0] + [pad] * (n - len(x[0])) for x in chunk])
        lab = torch.tensor([x[1] + [-100] * (n - len(x[1])) for x in chunk])
        att = torch.tensor([[1] * len(x[0]) + [0] * (n - len(x[0])) for x in chunk])
        yield ids, att, lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--per_conv", type=int, default=2, help="tutor turns sampled per conversation")
    ap.add_argument("--max_len", type=int, default=512)
    ap.add_argument("--micro_bs", type=int, default=2)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max_steps", type=int, default=0, help="stop early (smoke test)")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    torch.manual_seed(a.seed)
    tok = AutoTokenizer.from_pretrained(a.model)
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")
    model = AutoModelForCausalLM.from_pretrained(a.model, quantization_config=bnb, device_map="auto")
    model = prepare_model_for_kbit_training(model)  # also turns on gradient checkpointing
    model = get_peft_model(model, LoraConfig(
        r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    cand = HERE / "candidate"
    train = [encode(tok, h, r, a.max_len) for h, r in examples(cand / "train.jsonl", a.per_conv, a.seed)]
    val = [encode(tok, h, r, a.max_len) for h, r in examples(cand / "val.jsonl", 1, a.seed)]
    print(f"train examples {len(train)}, val examples {len(val)}")

    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.0)
    total = a.epochs * (len(train) // (a.micro_bs * a.accum))
    warm = max(1, int(0.05 * total))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / warm) * max(0.0, 1 - s / max(1, total)))
    scaler = torch.amp.GradScaler("cuda")
    rng, log, step, t0 = random.Random(a.seed), {"args": vars(a), "train": [], "val": []}, 0, time.time()

    def val_loss():
        model.eval()
        tot, n = 0.0, 0
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
            for ids, att, lab in batches(val, a.micro_bs, pad, False, rng):
                out = model(input_ids=ids.cuda(), attention_mask=att.cuda(), labels=lab.cuda())
                k = (lab[:, 1:] != -100).sum().item()
                tot += out.loss.item() * k
                n += k
        model.train()
        return tot / n

    log["val"].append({"step": 0, "loss": val_loss()})
    print("val loss before training", log["val"][-1]["loss"], flush=True)
    model.train()
    done = False
    for ep in range(a.epochs):
        acc, run = 0, 0.0
        for ids, att, lab in batches(train, a.micro_bs, pad, True, rng):
            with torch.autocast("cuda", dtype=torch.float16):
                loss = model(input_ids=ids.cuda(), attention_mask=att.cuda(), labels=lab.cuda()).loss / a.accum
            scaler.scale(loss).backward()
            run += loss.item()
            acc += 1
            if acc == a.accum:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                scaler.step(opt)
                scaler.update()
                opt.zero_grad()
                sched.step()
                step += 1
                acc = 0
                if step % 10 == 0:
                    log["train"].append({"step": step, "loss": run / 10})
                    print(f"step {step}/{total} loss {run / 10:.4f} {time.time() - t0:.0f}s", flush=True)
                    run = 0.0
                if a.max_steps and step >= a.max_steps:
                    done = True
                    break
        log["val"].append({"step": step, "loss": val_loss()})
        print(f"epoch {ep + 1} val loss {log['val'][-1]['loss']:.4f}", flush=True)
        if done:
            break
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"train_{a.name}.json").write_text(json.dumps(log, indent=1))
    model.save_pretrained(HERE / "adapters" / a.name)
    print("saved adapter", a.name, f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

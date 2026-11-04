"""Zero-shot baseline for a Socratic response model (run on a GPU, e.g. Colab/Kaggle).

For each test conversation, one tutor turn is picked (seeded). The model sees the system
prompt and the history before that turn and writes the next tutor message. Metrics against
the human tutor turn: ROUGE-L, ends-with-question rate, mean words, and the share of replies
that look like "telling" (contain no question and are long). Turns whose reference leaks the
answer are skipped.

    pip install -U transformers accelerate bitsandbytes rouge-score
    python eval_baseline.py --model microsoft/Phi-4-mini-instruct --name phi4mini
    python eval_baseline.py --model <gemma-4-E4B repo id> --name gemma4e4b
"""
import argparse, json, random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYSTEM_EXTRA = (" Guide the student with one short question at a time. Never state the final answer.")


def pick_turns(path, seed=42):
    rng, out = random.Random(seed), []
    for line in open(path, encoding="utf-8"):
        c = json.loads(line)
        msgs, leaks = c["messages"], c["tutor_leaks_answer"]
        idx = [i for i, m in enumerate(msgs) if m["role"] == "assistant"]
        ok = [(i, k) for k, i in enumerate(idx) if not leaks[k] and i > 0]  # i>0: some history exists
        if ok:
            i, _ = rng.choice(ok)
            out.append({"id": c["id"], "source": c["source"], "history": msgs[:i], "reference": msgs[i]["content"]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--adapter", default=None, help="LoRA adapter folder: evaluates the fine-tuned model")
    ap.add_argument("--max_new_tokens", type=int, default=80)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from rouge_score import rouge_scorer

    # 4-bit + fp16: fits a 16 GB T4 (no bf16 support there)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")
    multimodal = False
    try:
        tok = AutoTokenizer.from_pretrained(a.model)
        model = AutoModelForCausalLM.from_pretrained(a.model, quantization_config=bnb, device_map="auto")
    except Exception as e:  # e.g. Gemma 4: multimodal class
        print("CausalLM load failed, using multimodal class:", repr(e)[:200])
        from transformers import AutoProcessor, AutoModelForMultimodalLM
        tok = AutoProcessor.from_pretrained(a.model)
        model = AutoModelForMultimodalLM.from_pretrained(a.model, quantization_config=bnb, device_map="auto")
        multimodal = True
    if a.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter)
    scorer = rouge_scorer.RougeScorer(["rougeL"])
    rows = []
    turns = pick_turns(HERE / "candidate" / f"{a.split}.jsonl")
    for n, t in enumerate(turns, 1):
        if n % 20 == 0:
            print(f"{n}/{len(turns)}", flush=True)
        hist = [dict(m) for m in t["history"]]
        hist[0]["content"] += SYSTEM_EXTRA
        if multimodal:  # processor wants typed content parts
            hist = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in hist]
            ids = tok.apply_chat_template(hist, add_generation_prompt=True, tokenize=True, return_dict=True,
                                          return_tensors="pt")["input_ids"].to(model.device)
        else:
            ids = tok.apply_chat_template(hist, add_generation_prompt=True, tokenize=True, return_dict=True,
                                          return_tensors="pt")["input_ids"].to(model.device)
        with torch.no_grad():
            out = model.generate(ids, max_new_tokens=a.max_new_tokens, do_sample=False)
        reply = (tok.tokenizer if multimodal else tok).decode(out[0, ids.shape[1]:], skip_special_tokens=True).strip()
        rows.append({**t, "reply": reply, "rougeL": scorer.score(t["reference"], reply)["rougeL"].fmeasure})

    def rate(src, f):
        r = [x for x in rows if src in (None, x["source"])]
        return round(sum(f(x) for x in r) / len(r), 4)

    summary = {"model": a.model, "n": len(rows)}
    for src in (None, "mathdial", "socrateach"):
        k = src or "all"
        summary[k] = {
            "rougeL": rate(src, lambda x: x["rougeL"]),
            "asks_question": rate(src, lambda x: x["reply"].rstrip().endswith("?")),
            "mean_words": rate(src, lambda x: len(x["reply"].split())),
            "reference_mean_words": rate(src, lambda x: len(x["reference"].split())),
        }
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"{'tuned' if a.adapter else 'baseline'}_{a.name}.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

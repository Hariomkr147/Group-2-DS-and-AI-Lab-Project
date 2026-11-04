---
base_model: microsoft/Phi-4-mini-instruct
library_name: peft
pipeline_tag: text-generation
license: cc-by-nc-4.0
language:
- en
tags:
- base_model:adapter:microsoft/Phi-4-mini-instruct
- lora
- qlora
- transformers
- socratic-tutoring
- education
---

# Phi-4-mini Socratic tutor (LoRA adapter)

A LoRA adapter for [microsoft/Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct) that makes it reply like a Socratic maths tutor. It guides the student one step at a time with a short question or hint and does not state the final answer.

Weights: https://huggingface.co/IITM-2026T3-DSAI-GROUP2/Phi-4-mini-instruct-socratic-tutor

Built for the IIT Madras B.Sc. Data Science and AI Lab project (Group 2, Milestone 3).

## Usage

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

base = "microsoft/Phi-4-mini-instruct"
tok = AutoTokenizer.from_pretrained(base)
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
model = AutoModelForCausalLM.from_pretrained(base, quantization_config=bnb, device_map="auto")
model = PeftModel.from_pretrained(model, "IITM-2026T3-DSAI-GROUP2/Phi-4-mini-instruct-socratic-tutor")

system = ("You are a Socratic maths tutor. Guide the student one step at a time with questions and hints. "
          "Never state the final answer.\n\nProblem: {question}\n"
          "Correct final answer (for checking only, never reveal it): {answer}")
messages = [{"role": "system", "content": system.format(question="...", answer="...")},
            {"role": "user", "content": "student message"}]
prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
ids = tok(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
out = model.generate(**ids, max_new_tokens=96, do_sample=False, eos_token_id=[tok.eos_token_id, tok.convert_tokens_to_ids("<|end|>")])
print(tok.decode(out[0, ids["input_ids"].shape[1]:], skip_special_tokens=True))
```

The system prompt must use the same format as in training. The turn ends with `<|end|>`.

## Training

| | |
| --- | --- |
| Base model | `microsoft/Phi-4-mini-instruct` @ `cfbefacb`, loaded in 4-bit NF4 |
| Method | QLoRA, rank 16, alpha 16, dropout 0.05 |
| Target modules | `qkv_proj`, `o_proj`, `gate_up_proj`, `down_proj` (23.1M trainable parameters) |
| Data | 1,996 dialogues from the candidate subset: 1,000 SocraTeach_Multi and 1,000 MathDial, 4 dropped for length |
| Loss | Tutor turns only. Turns that give away the answer, and MathDial turns labelled "telling", are context without loss |
| Schedule | 1 epoch, effective batch 8, learning rate 2e-4, cosine, 5% warm-up, 8-bit paged AdamW, fp16 |
| Max length | 768 tokens |
| Hardware | Kaggle T4, about 49 minutes |

The setting was chosen from three candidates (r8 at 2e-4, r16 at 2e-4, r8 at 5e-5) trained on 400 dialogues: lowest validation loss among those that leak no more than 2 points above real tutors.

Code: `notes/sandeep/milestone-3/model_finetune/phi4mini-finetuning.ipynb`. It follows the Qwen 3.5-4B and Gemma 4 E4B notebooks by Hariom Kumar, so the three models can be compared on the same data and contexts.

## Results

100 held-out contexts (50 SocraTeach, 50 MathDial). The model writes the next tutor turn, greedy decoding, up to 96 new tokens.

| | leak rate | question rate | words | ROUGE-L | BLEU | val loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Real tutors | 0.01 | 0.62 | 22.2 | | | |
| Phi-4-mini, no training (4-bit) | 0.06 | 0.60 | 39.6 | 0.226 | 0.071 | 1.849 |
| **This adapter** | **0.00** | **0.65** | **21.8** | **0.294** | **0.174** | **1.166** |

Leak rate is the share of replies that state the final number before the student has said it. With 100 contexts, a difference of one or two leaks is within noise. There were no empty or runaway replies.

## Limits

- Evaluated on 100 contexts only. The MathDial test split (599 dialogues) is kept for the final evaluation.
- The leak check only covers single-number answers that are not already in the problem. Answers given in words are not caught.
- ROUGE-L and BLEU measure overlap with one real tutor reply, so a good reply that differs in wording scores low.
- Maths word problems in English only.

## Licence

The adapter is trained on SocraTeach_Multi (CC BY-NC 4.0) and MathDial (CC BY 4.0), so it is released for non-commercial use. The base model Phi-4-mini-instruct is MIT licensed.

## Framework versions

PEFT 0.21.2, Transformers 5.22.1, PyTorch 2.11.0

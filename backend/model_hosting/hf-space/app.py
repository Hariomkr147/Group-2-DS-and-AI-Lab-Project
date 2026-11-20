"""Space for the fine-tuned Qwen Socratic tutor (runs on ZeroGPU)."""
import spaces  # must be imported before torch

import os
import re

import gradio as gr
import torch
from huggingface_hub import file_exists
from peft import PeftConfig, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

TEST_ADAPTER = "IITM-2026T3-DSAI-GROUP2/qwen3-4b-ai-tutor-lora-latest"
ADAPTER_ID = os.getenv("QWEN_ADAPTER_ID") or TEST_ADAPTER
ADAPTER_REVISION = os.getenv("QWEN_ADAPTER_REVISION") or (
    "aaed93dd188ea65ffd2f5a547fdfb80ee6a5e0df" if ADAPTER_ID == TEST_ADAPTER else "main"
)
adapter = PeftConfig.from_pretrained(ADAPTER_ID, revision=ADAPTER_REVISION)
BASE_ID = os.getenv("QWEN_BASE_ID") or adapter.base_model_name_or_path
BASE_REVISION = os.getenv("QWEN_BASE_REVISION") or adapter.revision
MAX_NEW_TOKENS = 192     # same limit as the Kaggle hosting notebook
MAX_HISTORY = 12        # earlier turns are dropped so the prompt stays short

# The prompt the model was fine-tuned on. Keep the wording.
SYSTEM_TEMPLATE = (
    "You are a Socratic maths tutor. Guide the student one step at a time "
    "with questions and hints. Never state the final answer.\n\n"
    "Problem: {question}\n"
    "Correct final answer (for checking only, never reveal it): {answer}"
)

if file_exists(ADAPTER_ID, "tokenizer_config.json", revision=ADAPTER_REVISION):
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_ID, revision=ADAPTER_REVISION)
else:
    tokenizer = AutoTokenizer.from_pretrained(BASE_ID, revision=BASE_REVISION)
base = AutoModelForCausalLM.from_pretrained(BASE_ID, revision=BASE_REVISION, dtype=torch.bfloat16)
# torch_device="cpu": PEFT would otherwise load the adapter straight to CUDA, which ZeroGPU does not have at startup
model = PeftModel.from_pretrained(base, ADAPTER_ID, revision=ADAPTER_REVISION, torch_device="cpu")
model = model.merge_and_unload().eval().to("cuda")
STOP_IDS = sorted({tokenizer.eos_token_id, *tokenizer.encode("<|im_end|>", add_special_tokens=False)})


def _text(content) -> str:
    """Chat history content is a string, or a list of parts in newer Gradio versions."""
    if isinstance(content, str):
        return content
    return " ".join(part.get("text", "") for part in content if isinstance(part, dict))


def _generate(messages: list[dict]) -> tuple[str, bool]:
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, eos_token_id=STOP_IDS)
    generated = output[0, inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(generated, skip_special_tokens=True).strip()
    return text, len(generated) >= MAX_NEW_TOKENS


@spaces.GPU(duration=15)
def respond(message: str, history: list, problem: str, answer: str):
    """One tutoring turn in the demo chat."""
    if not message.strip() or not problem.strip() or not answer.strip():
        raise gr.Error("Fill in the problem, its correct answer and your message.")
    past = [{"role": m["role"], "content": _text(m["content"])} for m in history][-MAX_HISTORY:]
    system = SYSTEM_TEMPLATE.format(question=problem.strip(), answer=answer.strip())
    reply, _ = _generate([{"role": "system", "content": system}, *past, {"role": "user", "content": message.strip()}])
    shown = [*history, {"role": "user", "content": message.strip()}, {"role": "assistant", "content": reply}]
    return "", shown


@spaces.GPU(duration=15)
def predict(system: str, message: str) -> str:
    """Return the model's reply to one message under the given system prompt (at most 192 new tokens)."""
    if not message.strip():
        raise gr.Error("message is empty")
    messages = ([{"role": "system", "content": system}] if system.strip() else []) + [{"role": "user", "content": message}]
    return _generate(messages)[0]


@spaces.GPU(duration=15)
def predict_grounded(system: str, message: str) -> dict:
    """Return an NCERT reply with the status fields the backend checks."""
    if not system.strip() or not message.strip():
        raise gr.Error("Textbook context and a student message are required")
    text, at_limit = _generate([{"role": "system", "content": system}, {"role": "user", "content": message}])
    flags = []
    if re.search(r"</?think>", text, re.I):
        flags.append("reasoning_markup_present")
    if re.search(r"(?:^|\n)\s*(?:user|assistant|model|system|student|learner)\s*(?:[:\n])", text, re.I):
        flags.append("possible_invented_next_turn")
    return {"text": text, "task": "socratic_response_generation",
            "output_limit_reached": at_limit, "protocol_flags": flags}


with gr.Blocks(title="Qwen Socratic Tutor") as demo:
    gr.Markdown(
        "# Qwen Socratic Tutor\n"
        "A fine-tuned Qwen model that guides a learner with one question or hint at a time and does not give "
        "the final answer. Built by Group 2, Data Science and AI Lab, IIT Madras BS programme. "
        f"[Model card](https://huggingface.co/{ADAPTER_ID})\n\n"
        "**Research demo.** Replies can be wrong and are not approved for use with real learners. "
        "Do not enter personal information."
    )
    with gr.Row():
        problem = gr.Textbox(label="Problem", value="Solve 2x + 3 = 11.", scale=3)
        answer = gr.Textbox(label="Correct answer (the tutor must not reveal it)", value="4", scale=1)
    chat = gr.Chatbot(label="Tutoring session", height=380)
    message = gr.Textbox(label="Your message", placeholder="Type your attempt or ask for help, then press Enter")
    with gr.Row():
        send = gr.Button("Send", variant="primary")
        gr.ClearButton([chat, message], value="New session")
    gr.Examples(
        examples=[["Solve 2x + 3 = 11.", "4", "I am stuck. What should I do first?"],
                  ["What is 20% of 50?", "10", "I think it is 2.5"],
                  ["What is 1/2 + 1/3?", "5/6", "I added the tops and the bottoms and got 2/5."]],
        inputs=[problem, answer, message], cache_examples=False,
    )
    gr.Markdown("Replies are limited to 192 tokens and use greedy decoding. The first reply after a quiet period is slower.")

    message.submit(respond, [message, chat, problem, answer], [message, chat], api_name=False)
    send.click(respond, [message, chat, problem, answer], [message, chat], api_name=False)
    gr.api(predict, api_name="predict")
    gr.api(predict_grounded, api_name="predict_grounded")

demo.launch()

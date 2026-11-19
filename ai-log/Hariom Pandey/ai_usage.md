# AI Tutor – Prompt Engineering, LoRA Fine-Tuning and Evaluation

## 1. Project Overview

AI Tutor is an educational conversational assistant designed to help school students understand academic concepts through simple explanations, examples, hints, and guided learning.

The intended application allows students to select an NCERT textbook and chapter and ask questions related to the selected content. The tutor aims to behave like a patient teacher rather than simply providing direct answers.

### Key Objectives

- Provide student-friendly educational explanations.
- Explain concepts step by step.
- Help students solve mathematical problems through hints.
- Support Socratic tutoring and guided learning.
- Re-explain concepts using simpler language when required.
- Answer harmless general-purpose questions.
- Eventually provide textbook-grounded answers using NCERT content.

## 2. Model and Technical Environment

| Component | Details |
|---|---|
| Base Model | Qwen/Qwen3.5-4B |
| Fine-Tuning Method | LoRA |
| Training Platform | Kaggle |
| GPU | NVIDIA Tesla T4 |
| Number of GPUs | 1 |
| GPU Memory | 14.562 GB |
| Inference Framework | Unsloth |
| Model Repository | [Hugging Face Adapter](https://huggingface.co/IITM-2026T3-DSAI-GROUP2/NCERT-AI-Tutor-Qwen3.5-4B) |

**Important:** The Hugging Face repository contains a LoRA adapter and associated tokenizer/processor files. It is not a merged standalone model. The original base model must be loaded separately.

## 3. Dataset Preparation

The prepared dataset contained approximately 24,500 examples from the following sources:

1. SocraTeach
2. MathDial
3. Approximately 1,500 English curriculum examples from `FoundryAILabs/k12-indian-curriculum-4.9m`

The data was exported into JSONL files:

- `train.jsonl`
- `val.jsonl`
- `test.jsonl`

### Dataset Filtering

During preprocessing, the notebook applied two filtering conditions.

| Filtering Condition | Excluded Examples |
|---|---:|
| Examples without a user turn | 4,380 |
| Examples exceeding 512 tokens | 4,430 |
| Total Excluded | 8,810 |
| Retained Training Examples | 15,690 |

The first condition removed examples that did not contain a user turn and therefore could not form valid conversational training pairs.

The second condition removed examples exceeding the configured 512-token threshold. These examples were dropped entirely rather than truncated.

The final training dataset contained 15,690 examples, while the validation dataset contained 2,276 examples.

- Retention rate: 64.04%
- Exclusion rate: 35.96%

### Why Was a 512-Token Sequence Length Selected?

A maximum sequence length of 512 tokens was selected as an initial engineering trade-off.

The main considerations were:

1. **Hardware limitations:** Fine-tuning was performed on a single NVIDIA Tesla T4 GPU, making memory consumption an important consideration.
2. **Initial use cases:** The initial tutor focused on relatively short school-level questions, explanations, hints, and conversational exchanges.
3. **Training efficiency:** Shorter sequences make the initial fine-tuning experiment more manageable in terms of computational and memory requirements.

However, 512 tokens should not be considered a proven optimal sequence length.

This decision also introduced a limitation because longer educational examples were excluded. This may have reduced the model's exposure to detailed explanations and longer conversations.

Future experiments can evaluate 1,024 or 2,048 tokens, subject to hardware availability, along with length-aware batching, sequence packing, and carefully designed truncation or chunking strategies.

## 4. Training Instruction Design

One representative instruction from a SocraTeach example was:

> You are a patient Socratic math tutor. Guide the student with short questions and hints. Do not give the final answer before the student finds it. If the student makes a mistake, help them find it themselves.

This is a representative instruction from one dataset example, not a universal instruction used for every training record.

### Illustrative Educational Instruction Styles

**Mathematics**

Explain mathematical concepts step by step, use small numerical examples, provide hints, and check the student's understanding.

**Science**

Explain scientific concepts in age-appropriate language and connect them with everyday examples.

**Follow-up Learning**

If the student does not understand the previous explanation, explain the same concept using simpler words and a different example.

These instruction styles illustrate the educational approach used while designing the tutor.

## 5. Inference-Time System Prompts

Different system prompts were tested to improve the model's educational behaviour.

### Prompt 1: Initial Concise Tutor Prompt

```text
You are a patient and helpful AI tutor.
Explain concepts in simple language.
Guide students step by step.
```

### Prompt 2: Detailed Student-Facing Tutor Prompt

```text
You are a friendly AI tutor for school students.

Rules:
1. Speak directly to the student.
2. Use simple, age-appropriate English.
3. Explain concepts step by step.
4. Never display internal reasoning, analysis, or planning.
5. Start directly with the explanation.
6. Use one real-life example.
7. End with one question to check understanding.
8. Keep the answer clear and concise.
```

### Prompt 3: Expanded Evaluation System Prompt

```text
You are a friendly educational AI tutor.

Your primary purpose is helping students learn school subjects.

Instructions:
1. Explain educational topics in simple, age-appropriate language.
2. Give step-by-step explanations when needed.
3. Never provide incorrect formulas or facts.
4. Guide students using hints when they make mistakes.
5. You may also answer harmless general questions about movies, politics, relationships, computer science and daily life.
6. Be neutral when discussing politics.
7. Be empathetic and respectful when discussing relationships.
8. If you are uncertain, say so instead of inventing facts.
9. Do not show internal thinking or hidden reasoning.
10. Keep answers relevant to the question.
```

The prompts evolved from a simple tutor instruction into more detailed instructions that emphasized age-appropriate explanations, guided learning, response quality, and general-purpose conversational behaviour.

## 6. Initial Smoke Testing

Four initial questions were used to examine basic tutoring behaviour.

1. Explain photosynthesis to a Class 7 student using a simple real-life example.
2. Guide a Class 8 student who incorrectly believes that 3/4 + 1/2 = 4/6, using hints instead of immediately providing the answer.
3. Explain how to calculate the average speed of a train travelling 120 km in 2 hours.
4. Re-explain a previously discussed concept using simpler words and a different everyday example.

These questions examined basic educational explanations, Socratic guidance, mathematical teaching, and adaptive follow-up behaviour.

## 7. Twelve-Question Evaluation Set

The following questions were used in an earlier evaluation:

1. Explain photosynthesis with a simple real-life example.
2. A shopkeeper sells a pen for Rs. 20 and earns 25% profit. Find its cost price. Explain step by step.
3. Explain Newton's third law of motion with two everyday examples.
4. I think 1/2 + 1/3 = 2/5. Am I correct? Don't directly give me the answer. Help me understand my mistake using hints.
5. What is the difference between plant cells and animal cells? Explain in simple English.
6. Why do we see lightning before hearing thunder? Explain the scientific reason.
7. Explain the difference between physical change and chemical change with three examples.
8. Explain the difference between 'their', 'there', and 'they're' with examples.
9. A farmer has 17 sheep. All but 9 run away. How many sheep are left? Explain your reasoning.
10. I am unable to understand fractions. Teach me fractions as if I am a beginner, using a pizza example.
11. I still don't understand why plants need sunlight. Explain it again using simpler words and a different example.
12. If plants release oxygen during photosynthesis, does that mean plants do not need oxygen? Explain your answer.

## 8. Fifteen-Question Evaluation Set

An expanded evaluation was subsequently conducted using the third system prompt.

| No. | Category | Question |
|---:|---|---|
| 1 | Science | Explain photosynthesis with a simple real-life example. |
| 2 | Mathematics | A shopkeeper sells a pen for Rs. 20 and earns 25% profit. Find its cost price step by step. |
| 3 | Mathematics | I think 1/2 + 1/3 = 2/5. Am I correct? Guide me using hints. Do not directly give the answer. |
| 4 | Physics | Explain Newton's third law with two everyday examples. |
| 5 | Biology | What is the difference between plant cells and animal cells? |
| 6 | Chemistry | Explain physical and chemical changes with three examples each. |
| 7 | English | Explain the difference between their, there and they're with examples. |
| 8 | Reasoning | A farmer has 17 sheep. All but 9 run away. How many sheep are left? Explain. |
| 9 | Movies | What is the central message of the Indian movie 3 Idiots? Explain in simple English. |
| 10 | Politics | Explain the difference between democracy and dictatorship in a neutral and unbiased way. |
| 11 | Relationships | My best friend has stopped talking to me. What should I do? Give me some practical advice. |
| 12 | Computer Science | Explain binary search in simple language with an example. Why must the array be sorted? |
| 13 | Technology | What is the difference between Artificial Intelligence, Machine Learning and Deep Learning? |
| 14 | Cooking | Why does adding salt to water change its boiling point? Explain simply. |
| 15 | General Knowledge | Why does the sky appear blue during the day? Explain the science behind it. |

This evaluation examined both educational tutoring and general-purpose conversational behaviour.

## 9. LoRA Fine-Tuning Configuration

The completed fine-tuning run used the following configuration:

| Parameter | Value |
|---|---:|
| Base Model | Qwen/Qwen3.5-4B |
| Fine-Tuning Method | LoRA |
| GPU | NVIDIA Tesla T4 |
| Training Examples | 15,690 |
| Validation Examples | 2,276 |
| Maximum Training Steps | 180 |
| Per-Device Batch Size | 1 |
| Gradient Accumulation Steps | 16 |
| Effective Batch Size | 16 |
| Trainable Parameters | 19,378,176 |
| Total Parameters | 4,558,643,712 |
| Trainable Parameter Percentage | 0.43% |
| Training Duration | 53.7 minutes |
| Peak Training GPU Memory | 9.61 GB |
| Loss at Step 5 | 1.591369 |
| Final Loss at Step 180 | 1.027251 |

### Additional Training Observations

- FP16 was unavailable for this Qwen3.5 configuration in Unsloth, so the available FP32 fallback was used.
- The `causal_conv1d` dependency was missing, so the PyTorch reference implementation was used.
- A prompt/completion token-boundary mismatch warning appeared during tokenization, but training continued.
- The training run completed successfully.

A 1,500-step experiment was discussed as a possible future improvement. It was not completed and must not be considered part of the reported training results.

## 10. Hugging Face Upload and Inference

The trained adapter was uploaded to:

[NCERT AI Tutor – Qwen3.5-4B](https://huggingface.co/IITM-2026T3-DSAI-GROUP2/NCERT-AI-Tutor-Qwen3.5-4B)

The repository contained:

- `adapter_config.json`
- `adapter_model.safetensors`
- `chat_template.jinja`
- `processor_config.json`
- `README.md`
- `tokenizer_config.json`
- `tokenizer.json`

The adapter was successfully loaded and tested using Unsloth.

### Inference Loading Code

```python
import torch
from unsloth import FastLanguageModel

MODEL_ID = "IITM-2026T3-DSAI-GROUP2/NCERT-AI-Tutor-Qwen3.5-4B"

model, processor = FastLanguageModel.from_pretrained(
    model_name=MODEL_ID,
    max_seq_length=512,
    dtype=None,
    load_in_4bit=False,
)

FastLanguageModel.for_inference(model)
```

The processor/tokenizer chat template was used for generation.

During initial inference testing, a response displayed a visible "Thinking Process" section and was truncated at a 250-token generation limit. Later inference instructions explicitly told the model not to display internal reasoning.

## 11. Fifteen-Question Performance Evaluation

The expanded evaluation produced the following results:

| Metric | Result |
|---|---:|
| Total Questions | 15 |
| Non-Empty Responses | 15 |
| Empty Responses | 0 |
| Average Latency | 3.07 seconds |
| Average Generated Tokens | 56.8 |
| Average Generation Speed | 18.35 tokens/second |
| Average Response Length | 39.47 words |
| Peak GPU Memory | 8.7 GB |

### Educational Subset

| Metric | Result |
|---|---:|
| Questions | 8 |
| Average Latency | 3.14 seconds |
| Average Generated Tokens | 58.50 |
| Average Generation Speed | 18.48 tokens/second |
| Average Response Length | 35.5 words |
| Empty Responses | 0 |

### General-Purpose Subset

| Metric | Result |
|---|---:|
| Questions | 7 |
| Average Latency | 3.00 seconds |
| Average Generated Tokens | 54.86 |
| Average Generation Speed | 18.21 tokens/second |
| Average Response Length | 44.0 words |
| Empty Responses | 0 |

### Per-Question Performance

| Question | Latency | Generated Tokens | Tokens/sec |
|---:|---:|---:|---:|
| 1 | 2.26 s | 40 | 17.72 |
| 2 | 4.88 s | 94 | 19.28 |
| 3 | 2.13 s | 38 | 17.84 |
| 4 | 3.87 s | 74 | 19.13 |
| 5 | 2.21 s | 40 | 18.14 |
| 6 | 3.94 s | 75 | 19.02 |
| 7 | 3.37 s | 63 | 18.72 |
| 8 | 2.45 s | 44 | 17.97 |
| 9 | 2.43 s | 44 | 18.08 |
| 10 | 2.34 s | 42 | 17.94 |
| 11 | 2.56 s | 46 | 17.98 |
| 12 | 4.63 s | 87 | 18.78 |
| 13 | 3.31 s | 61 | 18.43 |
| 14 | 2.25 s | 40 | 17.77 |
| 15 | 3.46 s | 64 | 18.47 |

These measurements were obtained in the Kaggle Tesla T4 environment and should not be treated as performance guarantees for other hardware or production deployment.

## 12. Qualitative Evaluation

### Observed Strengths

- Clear and concise explanations of photosynthesis.
- Correct cost price calculation of Rs. 16 in the profit problem.
- Understandable explanation of Newton's third law.
- Clear comparison of plant and animal cells.
- Neutral political explanations.
- Empathetic relationship advice.
- Clear distinction between AI, ML, and DL.
- Correct reference to Rayleigh scattering in the blue-sky explanation.

### Observed Issues

1. An earlier fraction response incorrectly suggested adding denominators. A later response provided a better common-denominator hint.
2. The sheep riddle response encouraged the student to solve it rather than directly stating that 9 sheep remained.
3. The binary search fruit analogy was awkward.
4. Rusting was described as irreversible in a chemistry explanation. Irreversibility alone is not the definition of chemical change; the formation of a new substance is central.
5. "Their" was described as a possessive pronoun, whereas in the example it is more accurately a possessive determiner.

These are observations from a small 15-question evaluation, not statistically validated accuracy measurements.

## 13. Limitations

The current experiment has several limitations:

- Only 15 questions were used in the expanded evaluation.
- No formal accuracy benchmark was completed.
- Approximately 35.96% of prepared examples were excluded during filtering.
- Longer examples exceeding 512 tokens were dropped.
- Mathematical reliability requires further testing.
- Long multi-turn conversations were not comprehensively evaluated.
- NCERT chapter-specific retrieval was not established through this fine-tuning experiment.
- Production deployment was not confirmed.

## 14. Future Work

Planned improvements include:

- Expanding the educational evaluation dataset.
- Testing longer sequence lengths of 1,024 and 2,048 tokens.
- Improving the retention of longer educational examples.
- Exploring length-aware batching and sequence packing.
- Improving mathematical accuracy and verification.
- Improving Socratic hint generation.
- Adding grade-level adaptation.
- Testing longer multi-turn conversations.
- Evaluating hallucinations and factual consistency.
- Integrating NCERT textbook content through Retrieval-Augmented Generation (RAG).
- Developing an API and production deployment.
- Conducting longer fine-tuning experiments after validating the initial configuration.

These are future plans, not completed implementations.

## 15. Conclusion

The project successfully established an initial fine-tuned AI Tutor model based on Qwen3.5-4B using LoRA.

The adapter was uploaded to Hugging Face and successfully loaded for inference through Unsloth. Initial testing demonstrated that the model could generate responses to educational and general-purpose questions, with an average measured latency of 3.07 seconds across 15 questions in the Kaggle Tesla T4 environment.

The experiment also identified important areas for improvement, particularly mathematical reliability, longer educational contexts, and textbook-grounded question answering.

The completed work provides a foundation for developing a more capable NCERT-focused AI Tutor using improved data preparation, longer-context training, and Retrieval-Augmented Generation.

---

**Project Repository:** [Hugging Face – NCERT AI Tutor](https://huggingface.co/IITM-2026T3-DSAI-GROUP2/NCERT-AI-Tutor-Qwen3.5-4B)

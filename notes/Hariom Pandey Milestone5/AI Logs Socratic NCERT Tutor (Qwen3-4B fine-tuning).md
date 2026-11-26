# AI Logs: Socratic NCERT Tutor (Qwen3-4B fine-tuning)

Hariom Pandey | College project: Prerequisite-Aware Socratic AI Tutor

## 1. Where AI was used

| Part of the work | AI used | Role |
| --- | --- | --- |
| Planning, diagnosis and code | Claude (Anthropic) | Read my notebooks and the instructor feedback, explained the causes, wrote the notebook cells |
| Writing the synthetic tutoring chats | Qwen3-4B-Instruct-2507 (4-bit, Unsloth, on a Kaggle T4) | Generated tutor-student dialogues from NCERT text |
| Fact-check of the chats (Step 3D) | Qwen3-4B as judge, script written by another AI | Marked false praise, false "not quite" and wrong facts |
| Dataset merge and upload | Another AI assistant | Merged all sources into the final dataset |
| Model being trained | Qwen3-4B-Instruct-2507, QLoRA with Unsloth | The tutor model |

## 2. What I asked the AI assistant to do (my prompts, summarised)

1. Diagnose why the first model was inconsistent, leaked answers and agreed with wrong statements, using the instructor's feedback and my old notebooks.
2. Remove the off-domain data and the 512-token limit, and use as many tokens as a 16 GB T4 allows.
3. Build a better dataset with NCERT-grounded data, using my earlier pipeline notebook only as a reference.
4. Train with Unsloth, with checkpoints, so it can run overnight.
5. Measure the original Qwen before fine-tuning and the fine-tuned model after, with the same metrics: cross-entropy, perplexity, token accuracy, BLEU, ROUGE-L and behaviour tests.

## 3. The tutor system prompt

This prompt is used in training, in testing, and it must be the same in the backend.

```
You are a friendly and patient school tutor for Indian students (NCERT, Class 6-10: science, maths, social science).
Rules:
1. Help only with school-curriculum questions. If the student asks about something else (movies, songs, games, celebrities, etc.), politely say you can only help with school subjects, do not answer it, and bring the student back to the topic with one question. Do this even when the off-topic question uses a curriculum word.
2. Never say "correct", "right" or "you are correct" to a wrong or unsafe statement. Say clearly that it is not correct, then guide the student with a hint or a question.
3. For problems and reasoning questions, guide step by step with short questions and hints. Never give the final answer before the student finds it, even if the student asks for it.
4. For a simple fact, you may answer briefly, then check understanding with one question.
5. Safety first: if the student says something unsafe (tasting chemicals, touching live wires, etc.), firmly say it is unsafe and explain why.
6. Remember what was said earlier in the conversation and build on it. Keep replies short (1-4 sentences) and use simple English.
```

## 4. The prompt used to generate the NCERT dialogues

**Input to each generation:** a Class 6 to 10 NCERT topic with its textbook passage (from the KadamParth NCERT dataset), one key question and answer, and a scenario.

**Instruction (summarised):** "Write a realistic dialogue between a Class N student and a tutor. The passage is the only source of facts."

**Rules in the prompt:**

- The student talks like a real student: short and casual.
- The tutor is kind, uses simple English, writes 1 to 3 short sentences and asks one question in each turn.
- The tutor uses only facts from the passage and does not add new terms.
- The tutor says "correct" or "right" only when the student is fully right. Otherwise it says "not quite" and gives a hint.
- The tutor never gives the final answer before the student finds it.
- 3 to 5 student turns. The last tutor turn is a short summary without a question.

**The 8 scenarios:**

| Scenario | What the chat shows |
| --- | --- |
| guided concept | Student asks why or how, tutor guides with hints |
| misconception | Student says something wrong, tutor says "not correct" and guides |
| wrong attempt | Student answers wrongly, tutor says "not quite" and gives a hint |
| demand answer | Student says "just tell me the answer", tutor politely refuses and gives a hint |
| off-topic | Student asks for a movie or song using a school word, tutor refuses politely and redirects |
| direct fact | Short factual answer, then one check question |
| follow-up chain | Student's follow-up refers to earlier turns |
| unsafe claim | Student says something unsafe, tutor says it is not safe, explains why and gives the safe way |

**Parts written by me with fixed templates (not by the model), so they are always right:** the student's first line in the demand, off-topic and unsafe scenarios, and the tutor's first reply in the off-topic and unsafe scenarios.

**500 extra "just tell me the answer" chats in training:** the student's problem gets "Just tell me the answer." at the end, and the tutor starts with a polite refusal before the original guiding question.

## 5. Quality filters

- **Automatic rules:** correct turn order, no banned words, no "correct" to a question, a clear "not correct" or "not safe" where needed, a school redirect in off-topic chats, no answer leak in the first tutor turn.
- **Fact-check by a judge model:** it flagged 685 false "not quite", 248 bad facts and 82 false praise. 1,498 of 2,378 chats were kept.
- **Fact-check prompt (from the other AI):** PASTE THE PROMPT HERE.
- **Not done:** a human check of every chat.

## 6. Final training data and test prompts

- **Training:** 13,375 chats = 8,000 SocraTeach + 1,302 MathDial + 3,573 NCERT synthetic + 500 "demand answer" chats. The K12 direct-answer data was removed because it teaches "just answer". General chat data (UltraChat) was also removed on purpose.
- **Loss is computed only on the tutor's words.** The system prompt and the student text are masked. I checked this by printing an example.
- **Training setup:** Qwen3-4B-Instruct-2507, 4-bit QLoRA with Unsloth, max length 4096 tokens (the old limit was 512), about 836 steps, 1 epoch.
- **Evaluation prompts:** the instructor-style prompts (salt is H2O; tasting an acid; an Indian movie about acids and bases; a train-speed question with "just tell me the answer"), and 48 new questions written by the AI assistant: 10 off-topic, 10 unsafe, 12 false claims, 6 true claims and 10 maths questions with "just tell me the answer".
- **Metrics, base model vs fine-tuned:** cross-entropy, perplexity, token accuracy, BLEU, ROUGE-L, and behaviour pass rates (off-topic refusal, "not safe", no answer leak, "not correct" to wrong claims).

## 7. Limits (stated honestly)

- The dialogues are synthetic. They were generated and judged by a 4B model, not by teachers.
- The behaviour pass rates use simple text rules and can be wrong in some cases, so I also read sample replies.
- The data has fewer NCERT maths dialogues than science. Maths skill comes mostly from MathDial and SocraTeach.

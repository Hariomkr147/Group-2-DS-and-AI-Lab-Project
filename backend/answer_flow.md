# Answer flow

What the backend does after a learner answers a question (`app/services/tutor.py`, `controller.py`,
`socratic.py`, `misconception.py`, `step_finder.py`). The dashed box marks where the misconception stops.

```mermaid
flowchart TD
  A[Learner answers the question] --> B{Matches the correct answer?}

  B -- yes --> R1[learner_model.record correct]
  R1 --> C1{Current concept is the target?}
  C1 -- yes --> DONE[DONE]
  C1 -- no --> ADV[ADVANCE to next concept on stack]

  B -- no --> W{Did the learner show working?}
  W -- yes --> SF[Step finder: fine-tuned Qwen finds first wrong step]
  SF --> SF1{What did it find?}
  SF1 -- arithmetic slip --> N1[No misconception recorded]
  SF1 -- error sentence --> F1[found = model's error sentence]
  SF1 -- nothing --> MD
  W -- no --> MD[Rule detector: misconception.detect]

  MD --> P{An error pattern reproduces the answer?}
  P -- yes --> F2[found = pattern name]
  P -- no --> S{Expression search reproduces the answer?}
  S -- yes --> F3[found = search name]
  S -- no --> SM[Socratic model: socratic.diagnose_misconception]
  SM --> SN{Learner's answer is a number?}
  SN -- yes --> SC{Model's calculation uses the problem's numbers and equals the answer?}
  SC -- yes --> F5[found = model's sentence, checked]
  SC -- no --> F4[found = None]
  SN -- no --> F6[found = model's sentence, unchecked]
  SM -- "model off, down or unsure" --> F4

  N1 --> R2
  F1 --> R2
  F2 --> R2
  F3 --> R2
  F4 --> R2
  F5 --> R2
  F6 --> R2
  R2[learner_model.record wrong] --> CT{Any prerequisite with readiness below 0.6?}
  CT -- yes --> BT[BACKTRACK to weak prerequisite]
  CT -- no --> T{Wrong tries on this concept}
  T -- "1 to 2" --> HINT[HINT on same question]
  T -- "3 or more" --> PROBE[PROBE on same question]

  HINT --> SW
  PROBE --> SW
  BT --> SW
  ADV --> SW
  DONE --> SW
  SW[socratic.write: Qwen for HINT and PROBE, template otherwise] --> G[Guardrail: replace reply if it leaks the answer]
  G --> X{HINT or PROBE?}
  X -- "yes, wrong step known" --> X1[Prefix: Look again at step N]
  X -- "yes, no working" --> X2[Append: Show your steps]
  X -- no --> OUT
  X1 --> OUT
  X2 --> OUT
  OUT[TutorReply sent to frontend] --> UI[Chat shows Possible sticking point label when found is set]

  F1 -.-> GAP1[found is not passed to the controller or socratic.write]
  F2 -.-> GAP1
  F3 -.-> GAP1
  F5 -.-> GAP1
  F6 -.-> GAP1
  GAP1 -.-> UI

  classDef gap stroke-dasharray: 6 4,stroke-width:2px
  class GAP1 gap
```

Notes

- The next action depends only on right or wrong, prerequisite readiness and the try count.
- The misconception, found or not, never reaches the controller, the learner model or the reply writer. It is
  only shown as a label in the chat.
- The rule detector has three layers: error patterns, expression search, then the Socratic model. The model's
  suggestion is kept for a numeric answer only when its calculation reproduces the answer; a non-numeric answer
  cannot be checked, so its suggestion is unconfirmed.
- Hint and probe replies use the step finder's step number ("Look again at step N").

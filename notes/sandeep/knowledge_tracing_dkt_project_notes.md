# Knowledge Tracing (KT) --- Project Notes

## 1. What is Knowledge Tracing?

Knowledge Tracing (KT) is the process of estimating a student's
**current knowledge state** from their sequence of learning
interactions.

The basic idea is:

``` text
Student interactions
        ↓
Knowledge Tracing Model
        ↓
Estimated student knowledge state
        ↓
Personalization / Recommendation
```

For example, if a student repeatedly answers questions on fractions
incorrectly and later starts answering correctly, the KT model should
update its estimate of the student's knowledge of fractions.

------------------------------------------------------------------------

# 2. DKT --- Deep Knowledge Tracing

**DKT (Deep Knowledge Tracing)** is a neural-network-based approach to
Knowledge Tracing.

The original DKT approach uses an **LSTM/RNN** to process a sequence of
student interactions.

Example:

``` text
Student interaction history:

Fractions → Wrong
Fractions → Wrong
Fractions → Correct
Division  → Wrong
Fractions → Correct
```

The sequence is passed through the DKT model.

Conceptually:

``` text
Interaction 1 ──┐
Interaction 2 ──┤
Interaction 3 ──┤──→ LSTM ──→ hidden state
Interaction 4 ──┤
Interaction 5 ──┘
```

The hidden state represents a learned representation of what the model
currently believes about the student's knowledge.

------------------------------------------------------------------------

# 3. DKT Is Not Simply "Context Awareness"

DKT does capture context from previous interactions, but its purpose is
more specific than generic context awareness.

### Generic context

An LLM may use conversation history to understand:

> "What is the student talking about right now?"

### Knowledge Tracing

DKT tries to estimate:

> "What does the student currently know, based on their previous
> learning interactions?"

So:

``` text
Conversation context
        ≠
Knowledge state
```

They are related, but they solve different problems.

For an AI tutor, both may be needed.

------------------------------------------------------------------------

# 4. What Does DKT Actually Remember?

DKT maintains a hidden state while processing a sequence.

Conceptually:

``` text
h1 = state after interaction 1
h2 = state after interaction 2
h3 = state after interaction 3
...
ht = current state
```

Each new interaction updates the state.

For example:

``` text
Student answers Q1
       ↓
     DKT
       ↓
     h1

Student answers Q2
       ↓
     DKT
       ↓
     h2

Student answers Q3
       ↓
     DKT
       ↓
     h3
```

The latest hidden state contains information derived from the previous
sequence.

------------------------------------------------------------------------

# 5. Does DKT Memorize Individual Students?

Not in the sense that the trained neural network should simply memorize:

``` text
Student 1837 always gets Q23 wrong.
```

The trained model is intended to learn **general patterns of learning
behaviour** from many students.

For example:

> Repeated failures on a skill tend to indicate weaker knowledge of that
> skill.

At inference time, the student's own interaction history is used to
produce their current state.

So there are two different concepts:

### Model learning

The DKT model learns general patterns from the training population.

### Student state

For a particular student, the model processes their interaction sequence
and maintains an evolving state.

------------------------------------------------------------------------

# 6. Short-Term vs Long-Term Behaviour

DKT can process long interaction sequences, so it is not limited to only
a few questions.

However, a standard LSTM is not guaranteed to preserve every useful
detail from a very long history perfectly.

For example:

``` text
Day 1 ───────── Day 30 ───────── Day 60
  │                │                │
  └──────── interaction history ────┘
```

With very long histories, information from older interactions may become
less influential or difficult to retain.

Therefore:

> DKT should not be interpreted as a perfect database of everything a
> student has ever done.

It is better understood as a **learned representation of the student's
evolving knowledge state**.

------------------------------------------------------------------------

# 7. Raw History vs Current Knowledge State

A very important architectural distinction:

## Raw interaction history

This is the source data.

Example:

``` text
student_id | question | skill     | answer | timestamp
-----------|----------|-----------|--------|----------
S1         | Q101     | Algebra   | correct| ...
S1         | Q102     | Fractions | wrong  | ...
S1         | Q103     | Geometry  | correct| ...
```

This should normally be persisted.

## Current DKT state

This is derived from the interaction history.

Conceptually:

``` text
S1 → current DKT hidden state
```

The DKT state can be persisted as a cache/checkpoint for efficiency, but
it should not be treated as the only source of truth.

------------------------------------------------------------------------

# 8. Why Keep Raw History?

Raw history is useful even if DKT maintains the latest state.

It allows the system to:

-   Retrain the model
-   Replace DKT with another KT model
-   Compare DKT, AKT, BKT, etc.
-   Reconstruct a student's state
-   Debug incorrect predictions
-   Analyse learning behaviour
-   Build new features
-   Audit what happened during a student's learning journey

Therefore:

``` text
Raw history = Source of truth

DKT state = Derived / current state
```

------------------------------------------------------------------------

# 9. Conversations Are Different From Traditional KT Data

Traditional DKT datasets usually contain relatively structured
interactions such as:

``` text
(question_id, skill_id, correct/incorrect, timestamp)
```

An AI tutor has much richer conversations:

``` text
Student asks a question
Student asks for an explanation
Student asks for a hint
Student attempts a problem
Student makes a mistake
Student solves a problem
Student changes topic
Student asks a follow-up
```

It is not ideal to send the entire conversation directly into a
traditional DKT model.

Instead, an AI tutoring system can have an **interaction/event
extraction layer**.

``` text
Conversation
     ↓
LLM / NLP
     ↓
Learning Event Extraction
     ↓
Structured learning events
     ↓
Knowledge Tracing
```

For example:

``` text
Conversation:

Student:
"I don't understand quadratic equations."

Student:
"Give me another example."

Student attempts problem → Incorrect
```

Can be transformed into something like:

``` text
student_id: S1
skill: quadratic_equations
event: practice_attempt
outcome: incorrect
timestamp: ...
```

The structured learning event can then be used by the KT model.

------------------------------------------------------------------------

# 10. Session-Level and User-Level Knowledge State

For an AI tutor, it may be useful to maintain two scopes of state.

## User-level state

This represents the student's longer-term knowledge.

Example:

``` text
Student S1

Algebra       → 0.82
Fractions     → 0.45
Geometry      → 0.70
Calculus      → 0.30
```

This state persists across conversations/sessions.

It answers:

> "What do we currently believe this student generally knows?"

------------------------------------------------------------------------

## Session-level state

This represents the student's current learning state within one
conversation/session.

Example:

``` text
Session S101

Topic: Fractions

Initial state:
Fractions → 0.45

After several interactions:
Fractions → 0.62
```

This state is specific to the current session.

It answers:

> "What is happening with the student's understanding right now?"

------------------------------------------------------------------------

# 11. Session State and User State Are Different

The session state and user state should not necessarily be identical.

For example:

``` text
Long-term user state:

Fractions → 0.45
```

A new session starts:

``` text
User state
    ↓
Initialize session state
    ↓
Session state = 0.45
```

During the session, the student solves several problems correctly:

``` text
Session state → 0.65
```

We should not automatically conclude:

``` text
User state → 0.65
```

The session may contain only a small amount of evidence.

The long-term state should generally be more stable.

------------------------------------------------------------------------

# 12. A Better Mental Model

Think of the two states as:

``` text
User-level state
----------------
Long-term memory
Slow changing
Aggregated evidence from multiple sessions

          ▲
          │
    consolidation
          │
          │
Session-level state
-------------------
Short-term memory
Fast changing
Specific to current conversation
```

This gives the AI tutor both:

-   Long-term understanding of the student
-   Short-term understanding of the current learning session

------------------------------------------------------------------------

# 13. Do We Need Two DKT Models?

Not necessarily.

The model parameters can be shared.

Conceptually:

``` text
             One trained DKT model
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
    User-level state      Session-level state
       h_user                 h_session
```

The **model** is shared.

The **states** are different because they represent different
scopes/sequences.

We do not need to train one DKT model per student.

------------------------------------------------------------------------

# 14. Initializing a New Session

Suppose the user-level state is:

``` text
S1:

Algebra       0.80
Fractions     0.45
Geometry      0.70
Calculus      0.30
```

The student starts a new conversation about fractions.

The session can be initialized from the relevant user-level state:

``` text
User-level state
       ↓
Session initialization
       ↓
Session-level state
```

Then the session evolves independently as the student interacts with the
tutor.

------------------------------------------------------------------------

# 15. Updating the States

A naive approach would be:

``` text
Every interaction
       ↓
Update session state
       ↓
Update user state
```

This can work, but it can also cause problems.

For example:

``` text
One session
20 questions

       ↓

20 updates to user-level state
```

The user's long-term state may become overly influenced by one intensive
session.

A better architecture can be:

``` text
Interaction
     ↓
Update session state
     ↓
Session continues
     ↓
Session evidence / summary
     ↓
Update user-level state
```

Alternatively, user state can be updated continuously with a controlled
update/consolidation mechanism.

The exact strategy depends on the KT model and personalization
requirements.

------------------------------------------------------------------------

# 16. Suggested Architecture for an AI Tutor

A high-level architecture can look like this:

``` text
                         Student
                            │
                            ▼
                    Current Conversation
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
     Short-term context          Learning Event Extraction
                                             │
                                             ▼
                                      Structured Events
                                             │
                                             ▼
                                    Knowledge Tracing
                                             │
                              ┌──────────────┴──────────────┐
                              │                             │
                              ▼                             ▼
                       Session State                  User State
                       short-term                    long-term
                              │                             │
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                                      Personalization
                                             │
                                             ▼
                                  Next question / hint /
                                  explanation / content
```

------------------------------------------------------------------------

# 17. Persistence Strategy

A practical database design can have at least three logical areas.

## A. Conversation history

``` text
conversations
-------------
conversation_id
student_id
created_at
ended_at
```

``` text
messages
--------
message_id
conversation_id
role
content
timestamp
```

This stores the original conversation.

## B. Learning events

``` text
learning_events
---------------
event_id
student_id
conversation_id
skill_id
question_id
event_type
outcome
timestamp
```

This is the structured representation used for learning analytics/KT.

## C. Current student state

``` text
student_knowledge_state
-----------------------
student_id
model_version
state
updated_at
```

Optionally:

``` text
session_knowledge_state
-----------------------
session_id
student_id
model_version
state
updated_at
```

The exact representation of `state` depends on the KT model.

------------------------------------------------------------------------

# 18. Important Design Principle

Do not make the DKT state the only representation of student knowledge.

A safer architecture is:

``` text
                    Source of Truth
                          │
                          ▼
                 Raw interactions
                          │
                          ▼
                  Learning events
                          │
                          ▼
                 Knowledge model
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        Session state            User state
              │                       │
              └───────────┬───────────┘
                          ▼
                   Personalization
```

This allows the KT model to change without losing the student's history.

------------------------------------------------------------------------

# 19. DKT's Role in the Overall System

DKT should be viewed as one component of the personalization system.

``` text
Conversation
      ↓
Understand interaction
      ↓
Extract learning event
      ↓
Knowledge Tracing
      ↓
Estimate knowledge state
      ↓
Personalization engine
      ↓
Choose:
  - next question
  - difficulty
  - hint
  - explanation
  - revision topic
  - learning content
```

DKT itself does not decide everything the tutor should do.

It mainly provides a **learned estimate of the student's evolving
knowledge**.

------------------------------------------------------------------------

# 20. Example End-to-End Flow

Student S1 starts with:

``` text
User state:

Algebra    → 0.80
Fractions  → 0.45
Geometry   → 0.70
```

### New session

``` text
Student asks about fractions.

User state
    ↓
Session state initialized
    ↓
Fractions = 0.45
```

### Interaction 1

``` text
Student attempts question
→ Incorrect

Session DKT updates
→ Fractions = 0.38
```

### Interaction 2

``` text
Tutor explains the concept.

Student attempts another question
→ Correct

Session DKT updates
→ Fractions = 0.47
```

### Interaction 3

``` text
Student solves another question
→ Correct

Session DKT updates
→ Fractions = 0.55
```

### End of session

The system has evidence that the student improved during this session.

A consolidation mechanism can update the long-term state:

``` text
Previous user state
Fractions = 0.45

Session evidence
Fractions improved to ~0.55

Updated user state
Fractions = 0.48
```

The exact update is model/design dependent.

The important point is:

``` text
Session state = current learning trajectory

User state = long-term belief about the student
```

------------------------------------------------------------------------

# 21. Key Takeaways

1.  **DKT estimates an evolving student knowledge state from interaction
    sequences.**

2.  **DKT is not just generic context awareness.** It specifically
    attempts to model latent/evolving knowledge.

3.  **The trained DKT model learns general patterns across students.**
    It does not need to memorize each student as a separate model.

4.  **Raw interaction history should be persisted.** It is the source of
    truth.

5.  **The current DKT state is derived state.** It can also be persisted
    for efficiency.

6.  **Do not use the entire raw conversation directly as traditional DKT
    input.** Extract meaningful learning events first.

7.  **Session-level state and user-level state can both be maintained.**

8.  **Session state should generally be more responsive to recent
    interactions.**

9.  **User state should generally be more stable and represent long-term
    knowledge.**

10. **The same trained KT model can be used to maintain both states.**
    Separate models per student are not required.

11. **Do not blindly overwrite user state with session state.** Use a
    consolidation/update policy.

12. **Keep raw history even when current state is persisted.** This
    allows retraining, debugging, model replacement, and state
    reconstruction.

------------------------------------------------------------------------

# 22. Open Questions for the Project

Before implementing DKT, the project should answer:

-   What exactly is a "skill" or "concept" in our domain?
-   What constitutes a learning interaction?
-   How do we identify whether the student actually demonstrated
    knowledge?
-   Can an LLM reliably extract learning events from free-form
    conversation?
-   Should hints and explanations count as interactions?
-   How do we handle students changing topics within one conversation?
-   How should session state initialize from long-term user state?
-   How should session evidence update the long-term user state?
-   How long should session state live?
-   How do we handle very long student histories?
-   What happens when the KT model is replaced by a newer model?
-   Which KT model is best: DKT, BKT, AKT, SAKT, or another approach?
-   Is a neural KT model actually necessary for the available dataset
    size?
-   What metrics should be used to evaluate the KT model?
-   How will the estimated knowledge state drive personalization?

------------------------------------------------------------------------

## Final Mental Model

The simplest way to remember the architecture is:

``` text
                  RAW HISTORY
                       │
                       ▼
              Learning Events
                       │
                       ▼
                 KT Model
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
       USER STATE            SESSION STATE
      Long-term               Short-term
            │                     │
            └──────────┬──────────┘
                       ▼
                PERSONALIZATION
                       │
                       ▼
              What should we
              do for the student
              next?
```

**Core principle:**

> Raw history tells us what happened.\
> Knowledge Tracing estimates what the student currently knows.\
> Session state captures what is happening now.\
> User state captures what we believe the student knows over the long
> term.\
> Personalization uses these states to decide what to do next.

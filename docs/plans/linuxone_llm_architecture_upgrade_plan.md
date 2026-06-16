# LinuxONE Knowledge Assistant — LLM Architecture Upgrade Plan

## Objective

Upgrade the current LAG/RAG answer-generation architecture so the LinuxONE Knowledge Assistant produces **stable, complete, source-grounded answers** without premature truncation or inconsistent first-pass quality.

This upgrade is specifically intended to solve the current issue where:
- the **first answer is sometimes truncated or incomplete**
- a manual **regenerate** often produces a **better, fuller answer**
- the current architecture does not distinguish between:
  - a complete answer
  - a truncated answer
  - a poor first-pass answer
  - a true technical error

The goal is to make the answer pipeline production-ready by adding:
- better prompting for evidence-backed RAG
- stronger generation controls
- completion integrity checks
- hidden continuation fallback
- conditional hidden full regenerate
- better logging and observability
- clearer internal state handling

---

# Problem Summary

## Current behavior
The current implementation sends a single prompt to Ollama/Qwen and treats any returned text as final.

This causes the following problems:

1. **Premature truncation is treated as success**
   - If the model stops mid-sentence, the answer is still shown as final.

2. **Manual regenerate often gives a better answer**
   - This implies the first pass is not always stable or fully synthesized.

3. **No answer integrity validation exists**
   - The backend does not check whether the response looks incomplete.

4. **The prompt is under-constrained for evidence-backed RAG**
   - It encourages “best possible” synthesis rather than strict source grounding.

5. **No distinction exists between valid incomplete evidence vs generation failure**
   - The system cannot tell the difference between:
     - no relevant information
     - truncated answer
     - actual backend failure

---

# Target Architecture

Implement a **multi-stage answer generation pipeline** with validation and repair.

## Target flow

```text
User Query
   ↓
Retrieve + Rerank Source Chunks
   ↓
Generate Initial Answer
   ↓
Validate Completion Integrity
   ├── If complete → return final answer
   └── If incomplete → run hidden continuation
                  ↓
           Validate again
           ├── If complete → return repaired answer
           └── If still poor/incomplete → hidden full regenerate
                                   ↓
                              Validate again
                              ├── If complete → return regenerated answer
                              └── If failed → graceful failure state
```

---

# Key Architectural Principles

## 1) Treat truncation as a recoverable generation problem
A truncated answer is **not** a successful answer and **not** a technical failure.
It is a recoverable generation state.

## 2) Continuation is better than immediate regenerate
If the answer is cut off, the first fallback should be:
- continue the same answer
- using the same retrieved context
- without restarting

This is preferable to immediate regenerate because it:
- preserves continuity
- reduces drift
- is cheaper
- is faster
- is more stable for a source-grounded assistant

## 3) Full hidden regenerate should be conditional, not automatic
A full regenerate is useful as a fallback, but should only happen when:
- continuation fails
- the response still looks incomplete
- or the first-pass synthesis appears weak/unreliable

## 4) No-sources is a valid product state
If retrieval found no useful evidence, the system should return a polished no-evidence response.
This is different from:
- truncation
- system error
- timeout

## 5) Production credibility depends on answer stability
The answer pipeline should prioritize:
- completeness
- groundedness
- consistency
- graceful recovery

---

# Required Backend State Model

Implement explicit internal states for generation.

## Retrieval / response states

```python
class AnswerStatus:
    IDLE = "idle"
    RETRIEVING = "retrieving"
    GENERATING = "generating"
    VALIDATING = "validating"
    CONTINUING = "continuing"
    REGENERATING = "regenerating"
    COMPLETE = "complete"
    NO_SOURCES = "no_sources"
    ERROR = "error"
```

## Meaning of each state

- `idle` → no request yet
- `retrieving` → retrieving source chunks
- `generating` → initial LLM answer in progress
- `validating` → checking whether output is complete and usable
- `continuing` → hidden continuation pass is running
- `regenerating` → hidden full regenerate pass is running
- `complete` → stable final answer ready
- `no_sources` → no sufficiently relevant evidence found
- `error` → actual technical failure

Important: **do not merge `no_sources` and `error`.**

---

# Upgrade Requirements by Layer

## Layer 1 — Prompting

### Problems in current prompt
The existing prompt has several weaknesses:
- malformed quote in the continuation-related instruction
- references to “output window,” which is a UI concept rather than a model concept
- asks the model not to truncate, which is not reliable
- says “provide the best possible answer using the available information,” which encourages unsupported inference
- does not strongly enforce source grounding

### Required prompting changes

#### Initial answer prompt must:
- define the assistant as a LinuxONE evidence-backed assistant
- require the model to use only the provided source context
- prohibit unsupported invention/inference
- instruct the model to say when evidence is insufficient
- require a concise but complete answer
- require a clean ending with a complete sentence
- avoid meta language like “based on the provided context” unless you explicitly want that style

#### Continuation prompt must:
- state that the previous answer was incomplete
- include the original question
- include the same retrieved source context
- include the partial answer
- instruct the model to continue from where it stopped
- explicitly forbid restarting or repeating previously generated content
- require ending with a complete sentence

#### Full regenerate prompt must:
- be stricter than the initial prompt
- use low temperature
- explicitly prioritize completeness and grounding
- require a stable final response

---

## Layer 2 — Retrieval Context Handling

### Current behavior
The service enforces a context token budget and uses chunks until the budget is filled.
This is directionally correct, but quality depends on:
- chunk ranking quality
- chunk order quality
- whether the highest-value chunks are included first

### Required context handling rules

1. Continue using a max context budget.
2. Ensure the **highest-confidence chunks** are included first.
3. Use the **same context for continuation**.
4. Only consider **fresh retrieval / reranking on full regenerate**.
5. Preserve source ordering consistency so the answer remains aligned with the displayed sources.

### Recommendation
If retrieval ranking is not already strong, ensure the chunk list passed into `LLMService` is already:
- ranked by relevance
- deduplicated if possible
- trimmed to the most salient evidence

---

## Layer 3 — Generation Controls

### Current problems
- function signature accepts `temperature`, but request hardcodes `0.3`
- generation settings are not optimized for a strict RAG QA workflow
- no generation metadata is used for validation

### Required generation behavior
For evidence-backed QA, reduce variability.

#### Recommended defaults
- `temperature`: `0.1` to `0.2`
- `top_p`: `0.85` to `0.9`
- `repeat_penalty`: keep around `1.1` to `1.15`
- `num_predict`: high enough to avoid premature cutoff for normal answers

### Requirement
Use the method parameters rather than hardcoded values where possible.

---

## Layer 4 — Completion Integrity Validation

This is the most important missing layer in the current architecture.

### Goal
Never treat a suspiciously incomplete answer as final.

### Implement a `looks_incomplete()` validator
The validator should inspect:
- provider finish reason metadata
- text ending quality
- structural completeness

### Strong incompleteness signals
Flag the answer as incomplete if any of the following are true:

1. `done_reason` indicates a token cap / length stop
2. answer ends mid-sentence
3. answer ends without terminal punctuation in a suspicious way
4. last word is a dangling connector such as:
   - `and`
   - `or`
   - `with`
   - `within`
   - `of`
   - `to`
   - `for`
   - `including`
   - `that`
   - `which`
5. numbered or bulleted structure appears incomplete
6. markdown or formatting syntax strongly suggests cutoff

### Important note
A short answer is not necessarily incomplete.
The validator should distinguish between:
- a concise complete answer
- a clearly cut-off answer

---

## Layer 5 — Hidden Continuation Step

### Purpose
If the answer appears incomplete, attempt a hidden continuation before doing a full regenerate.

### Continuation rules
- use the **same question**
- use the **same retrieved context**
- include the **partial answer**
- instruct the model to continue exactly where it stopped
- forbid restarting the answer
- forbid repeating prior text
- require a complete ending

### Why continuation comes before regenerate
Because this is a truncation repair step, not a synthesis replacement step.

### Output handling
The continuation output should be appended to the partial answer only after:
- trimming duplicates if necessary
- validating the resulting combined answer

---

## Layer 6 — Conditional Hidden Full Regenerate

### Purpose
Use this only when continuation fails or the first-pass answer appears unreliable.

### When to trigger full regenerate
Trigger only if one or more of the following are true:
- initial answer incomplete and continuation still incomplete
- initial answer complete structurally but clearly poor/off-target
- answer is unstable or weak relative to retrieval context
- no adequate completion was produced after continuation

### Full regenerate rules
- optionally reuse the same context first
- optionally rerun retrieval/reranking if retrieval may have been weak
- lower temperature further if needed
- use stricter formatting/grounding instructions

### Important rule
Do **not** silently run a full regenerate for every request.
That would:
- increase cost
- increase latency
- increase inconsistency risk
- hide root-cause issues

---

## Layer 7 — Graceful Failure Handling

If generation still fails after repair attempts, return a graceful backend failure result.

### Correct product treatment
This is not a no-sources state.
This is not a user error.
This is a generation failure.

### Suggested fallback message
> I found relevant sources, but I couldn’t generate a stable final answer this time. Please try again.

This should be rare and used only after repair attempts fail.

---

# Required Changes to `LLMService`

The current `LLMService` should be upgraded rather than replaced conceptually.

## Required methods
The upgraded service should include at minimum:

```text
generate_response()
_build_prompt()
_build_continuation_prompt()
_build_regenerate_prompt()   # optional helper if regenerate differs
_looks_incomplete()
continue_response()
regenerate_response()        # conditional hidden regenerate
_calculate_context_tokens()
_enforce_token_budget()
```

---

# Detailed Implementation Plan

## Phase 1 — Fix the existing prompt architecture

### Tasks
1. Remove malformed continuation-related instruction.
2. Remove “You are strictly prohibited from truncation.”
3. Remove “best possible answer using the available information” wording.
4. Replace with explicit evidence-backed rules.
5. Require complete final sentence.
6. Keep the answer style concise and source-grounded.

### Success criteria
- prompt is clean and deterministic
- prompt does not encourage filler or unsupported inference
- prompt does not use ambiguous UI-based language

---

## Phase 2 — Improve generation configuration

### Tasks
1. Stop hardcoding temperature inside the request body.
2. Use the function parameter in the request payload.
3. Lower default temperature to approximately `0.15`.
4. Keep `top_p` controlled.
5. Ensure `num_predict` is sufficient for normal answers.

### Success criteria
- answer variance is reduced
- answer quality is more stable across repeated asks
- method parameters reflect actual request behavior

---

## Phase 3 — Capture and log model generation metadata

### Tasks
1. Capture and return:
   - `done`
   - `done_reason`
   - `prompt_eval_count`
   - `eval_count`
   - total token counts
2. Log these values for every request.
3. Log whether continuation/regenerate was triggered.

### Why this is necessary
Without generation metadata, truncation diagnosis remains guesswork.

### Success criteria
- logs clearly reveal whether completion ended due to token cap or another reason
- repair decisions become traceable

---

## Phase 4 — Add completion integrity validation

### Tasks
1. Implement `_looks_incomplete(text, done_reason)`.
2. Use both provider metadata and text heuristics.
3. Apply this check to every initial answer.
4. Optionally apply the same check after continuation/regenerate.

### Success criteria
- incomplete first-pass answers no longer go directly to the UI as final
- false positives remain low for short but complete answers

---

## Phase 5 — Add hidden continuation repair

### Tasks
1. Implement `continue_response()`.
2. Build a continuation prompt that includes:
   - original question
   - same source context
   - partial answer
3. Forbid restart/repetition.
4. Merge partial + continuation safely.
5. Revalidate the combined result.

### Success criteria
- clearly truncated answers are automatically repaired without visible user action
- continued answers remain aligned with the same sources

---

## Phase 6 — Add hidden full regenerate fallback

### Tasks
1. Implement `regenerate_response()`.
2. Trigger only if continuation failed or answer still looks unreliable.
3. Optionally rerun retrieval only at this stage.
4. Use stricter regeneration prompt.
5. Revalidate regenerated output before returning.

### Success criteria
- regenerate is a fallback, not default behavior
- answer stability improves while cost remains controlled

---

## Phase 7 — Separate no-sources from generation failure

### Tasks
1. Ensure retrieval layer can return a `no_sources` outcome before generation.
2. If no qualifying context chunks are available, skip normal answer generation.
3. Return a dedicated no-evidence response.
4. Do not send empty/weak retrieval context to the model and hope it recovers.

### Success criteria
- lack of evidence is communicated clearly and honestly
- no-sources does not masquerade as an LLM failure

---

## Phase 8 — Add backend observability and diagnostics

### Log for each request
At minimum, log:
- request ID
- query text or hashed query identifier
- number of retrieved chunks
- estimated context tokens
- prompt token count
- completion token count
- finish reason / done status
- whether incomplete heuristic fired
- whether continuation fired
- whether full regenerate fired
- final status
- total latency

### Why this matters
This allows you to measure:
- how often truncation really happens
- whether continuation helps
- whether regenerate is overused
- whether token caps are too low

---

# Recommended Internal Decision Flow

Use this backend decision model.

```text
1. Retrieve source chunks
2. If no relevant chunks → return no_sources
3. Generate initial answer
4. Validate answer integrity
   - If complete → return final
   - If incomplete → continue with same context
5. Validate repaired answer
   - If complete → return final
   - If incomplete/poor → full regenerate
6. Validate regenerated answer
   - If complete → return final
   - Else → generation failure fallback
```

---

# Prompt Templates to Implement

## 1) Initial answer prompt

### Intent
Stable first-pass evidence-backed answer.

### Required characteristics
- anchored to source context only
- concise but complete
- no unsupported synthesis
- complete ending

### Template guidance

```text
You are LinuxONE Assistant, an evidence-backed assistant for LinuxONE and IBM technologies.

Answer the user's question using ONLY the provided source context.
Do not invent or infer information that is not supported by the sources.
If the sources do not contain enough information to answer confidently, say so clearly.

Context:
{context}

User question:
{query}

Instructions:
- Give a concise but complete answer.
- Use short paragraphs or bullet points when helpful.
- Base every claim on the provided sources only.
- Do not repeat yourself.
- If the evidence is limited, state that clearly.
- End with a complete sentence.
- Do not include filler or meta commentary.

Answer:
```

---

## 2) Continuation prompt

### Intent
Repair a truncated answer without changing the evidence set.

### Template guidance

```text
The previous answer was cut off and is incomplete.

Use ONLY the source context below and continue the answer from exactly where it stopped.

Context:
{context}

User question:
{query}

Partial answer:
{partial_answer}

Instructions:
- Continue from the partial answer.
- Do not restart the answer.
- Do not repeat prior content.
- Do not add unsupported information.
- Finish the answer cleanly.
- End with a complete sentence.

Continuation:
```

---

## 3) Full regenerate prompt

### Intent
Produce a stable full replacement answer only when continuation failed.

### Template guidance

```text
You are LinuxONE Assistant, an evidence-backed assistant for LinuxONE and IBM technologies.

Generate a stable, complete answer using ONLY the source context below.
Do not infer unsupported details.
If the evidence is incomplete, say so clearly.

Context:
{context}

User question:
{query}

Instructions:
- Provide a complete answer.
- Prefer bullet points when the question asks for features, benefits, steps, or categories.
- Keep the answer grounded in the sources.
- Do not repeat yourself.
- End with a complete sentence.

Answer:
```

---

# Validation Heuristics Specification

Implement a dedicated incompleteness heuristic.

## Strong signals
- provider `done_reason` indicates length cap
- response ends in a dangling connector word
- response lacks terminal punctuation and is sufficiently long to suggest it is not intentionally fragmentary
- final list item appears incomplete

## Weak signals
- unusually short completion token count despite many retrieved chunks
- abrupt end after a colon or list introduction
- open structured content with missing closure

## Safety rule
Do not over-trigger continuation for concise but complete answers.

---

# Regenerate Policy

## Recommended policy

### Use hidden regenerate only if:
- initial answer incomplete and continuation failed
- answer is structurally complete but weak/off-target
- model output quality is unstable after first repair pass

### Do not use hidden regenerate if:
- answer is already complete and grounded
- no-sources should have been returned instead
- the issue is obviously a true technical failure

### Fresh context policy
- **Continuation** should use the same retrieval context.
- **Full regenerate** may optionally use updated retrieval if reranking quality is uncertain.

---

# Suggested Return Shape

Upgrade the service response payload to expose enough metadata for the application layer.

## Suggested response fields

```python
{
    "answer": str,
    "model": str,
    "status": "complete" | "no_sources" | "error",
    "repair_strategy": "none" | "continued" | "regenerated",
    "done": bool,
    "done_reason": str | None,
    "prompt_tokens": int,
    "completion_tokens": int,
    "total_tokens": int,
    "context_chunk_count": int,
    "context_estimated_tokens": int,
}
```

This makes debugging and product behavior easier.

---

# Frontend / Product Implications

The frontend does not need big structural changes for this architecture upgrade, but it should support the backend states gracefully.

## Recommended UI behavior

### During backend recovery
If the first pass is being validated or repaired, the UI can remain in a subtle pending/finalizing state.

Preferred behavior:
- avoid showing a clearly truncated answer as final immediately
- wait until validation/repair completes when possible
- optionally show subtle metadata state such as:
  - “Finalizing answer…”

### If repair ultimately fails
Show a polished retryable failure message rather than displaying broken output.

---

# Testing Plan

## 1) Unit tests
Add tests for:
- `_looks_incomplete()` with complete answers
- `_looks_incomplete()` with truncated endings
- `_looks_incomplete()` with dangling connector endings
- continuation merge behavior
- no-sources branching

## 2) Integration tests
Test full flow for:
- complete first-pass answer
- initial truncation recovered by continuation
- continuation failure recovered by regenerate
- no-sources result
- technical timeout / API failure

## 3) Adversarial tests
Use queries that often trigger longer outputs, such as:
- “What are the security features of LinuxONE?”
- “Explain LinuxONE resiliency and disaster recovery in detail.”
- “List LinuxONE virtualization capabilities and operational benefits.”

These should be tested repeatedly to assess stability.

## 4) Regression tests
Compare:
- first-pass completion rate before vs after
- regenerate frequency before vs after
- average answer length stability
- no-sources accuracy

---

# Metrics to Track

Track these metrics so the upgrade can be evaluated objectively.

## Core quality metrics
- percentage of initial answers flagged as incomplete
- percentage of incomplete answers repaired by continuation
- percentage requiring full regenerate
- final answer success rate
- average answer token length
- answer latency

## Reliability metrics
- timeout rate
- backend error rate
- no-sources rate
- percent of responses ending with suspicious truncation

## Product metrics
- manual regenerate click rate before/after
- user satisfaction or thumbs-up rate if available
- copy/retry frequency if available

---

# Acceptance Criteria

The architecture upgrade is successful when all of the following are true:

1. Clearly truncated first-pass answers are no longer returned directly as final.
2. The backend automatically detects and repairs incomplete answers.
3. Continuation is used before full regenerate.
4. Full regenerate is conditional, not default.
5. No-sources is cleanly separated from technical failure.
6. Prompting is stricter and more grounded than the current implementation.
7. Generation settings are deterministic enough for production RAG behavior.
8. Logging exposes enough metadata to diagnose remaining failures.
9. Manual regenerate frequency decreases materially.
10. Final answers are more stable, complete, and source-grounded.

---

# Recommended Execution Order

## Step 1
Refactor the prompts.

## Step 2
Fix generation options so request parameters are actually respected.

## Step 3
Add logging for finish metadata.

## Step 4
Implement `_looks_incomplete()`.

## Step 5
Implement `continue_response()`.

## Step 6
Add continuation into `generate_response()`.

## Step 7
Implement `regenerate_response()` as fallback.

## Step 8
Separate `no_sources` from `error` clearly.

## Step 9
Add tests and metrics instrumentation.

---

# Brief Agent Prompt

Use this if you want a shorter implementation directive for the coding agent:

```text
Upgrade the LinuxONE Knowledge Assistant LLM architecture so that incomplete first-pass answers are automatically detected and repaired.

Requirements:
- Refactor the current LLMService into a multi-stage answer pipeline.
- Keep the current RAG model, but improve stability and completeness.
- Tighten the prompt so answers use ONLY the provided source context.
- Remove malformed/ambiguous anti-truncation instructions from the current prompt.
- Lower generation variability for production RAG behavior.
- Capture and log completion metadata such as done/done_reason and token counts.
- Implement a looks_incomplete() validator using finish metadata + text heuristics.
- If an answer looks incomplete, run a hidden continuation step using the same query + same retrieved context + partial answer.
- Do not restart the answer during continuation.
- Only if continuation fails, run a hidden full regenerate.
- Full regenerate should be conditional, not automatic for every request.
- Separate valid no-sources outcomes from technical errors.
- Return richer metadata about repair strategy and completion status.
- Add tests for complete answers, truncated answers, continuation recovery, regenerate fallback, no-sources, and technical failure.

Goal:
Produce more stable, complete, source-grounded answers while reducing manual regenerate reliance.
```

---

# Final Recommendation

Do **not** solve the current problem by blindly regenerating every answer in the background.

Instead, implement this architecture:

1. initial generation
2. completion validation
3. hidden same-context continuation if incomplete
4. hidden full regenerate only if continuation fails

That is the correct production-grade upgrade for an evidence-backed LinuxONE assistant.

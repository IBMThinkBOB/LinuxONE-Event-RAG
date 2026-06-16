# Diagnosing RAG Answer Quality Issues: Five Likely Causes and How to Solve Them

## Overview

This document summarizes the five most likely causes of the current answer-quality issues in the LinuxONE RAG system and explains how to address each one.

The five likely causes are:

1. **Multi-chunk synthesis failure**
2. **Weak source grounding / generic prior override**
3. **Prompt procedural noncompliance**
4. **Chunk noisiness / fragmentation**
5. **Retrieval irrelevance / ranking mismatch**

The current system already has:
- a standard embedding model (`sentence-transformers/all-MiniLM-L6-v2`) generating embeddings, which is a reasonable baseline for retrieval pipelines. citeturn31search2
- an LLM prompt design that already contains strong instructions about using context, multiple sources, and completeness, which suggests that adding more prompt wording alone is unlikely to fully solve the issue. citeturn31search3

So the problem is not just “the prompt needs to be stronger.” It is more likely a combination of retrieval behavior, chunk quality, evidence shaping, and model grounding.

---

## 1) Multi-chunk synthesis failure

### What it means
The model is **not combining multiple retrieved chunks into a unified answer**. Instead, the behavior looks like this:

```text
Retrieve 5 chunks
→ Read chunk 1 or the strongest chunk
→ Generate answer
→ Stop
```

This is the most likely explanation for cases where:
- the answer is short
- the answer is somewhat correct
- but the answer reflects only one idea from the retrieved context

This matches examples like “What AI frameworks are supported on LinuxONE?” where the answer appears to come from one chunk listing frameworks and then stops.

### Why it causes current outputs
When a question can be answered by a single chunk, the model decides that the answer is complete. The prompt may say “be complete,” but the model interprets that as:

- “I found the answer”
- not “I synthesized everything relevant”

This is especially problematic for broad questions such as:
- hardware capabilities
- high availability
- performance benchmarks
- enterprise applications

These require **aggregation across categories**, not just one supporting paragraph.

### How to solve it

#### A. Change the answering task from “answer the question” to “extract + aggregate + answer”
A stronger architecture is:

```text
Step 1: identify which chunks are relevant
Step 2: extract bullet-point facts from each relevant chunk
Step 3: combine those facts into the final answer
```

This can be implemented in a single prompt or in multiple stages, but the key is to force the model to perform intermediate evidence extraction rather than answering immediately.

#### B. Group chunks by subtopic before generation
If retrieved chunks cover multiple dimensions such as:
- PR/SM / LPAR
- failover networking
- hardware sparing
- power/cooling redundancy

then the chunks should not just be passed as five raw paragraphs in sequence. Instead, the context should be organized into explicit topic groups.

#### C. Enforce “coverage dimensions,” not just “use multiple sources”
It is stronger to say:

```text
Cover all major relevant dimensions present in the context.
```

than:

```text
Use multiple sources.
```

For example, for high availability, the answer should ideally cover:
- virtualization isolation
- failover mechanisms
- hardware sparing
- infrastructure redundancy

#### D. Add a pre-answer extraction layer
Each chunk can first be converted into a normalized evidence summary like:

```text
Source 1:
- PR/SM creates isolated LPARs
- supports dynamic allocation
- has automation for HA

Source 2:
- VSWITCH failover
- link aggregation
- network redundancy

Source 3:
- transparent core sparing
- redundant clocks
- N+1 power/cooling
```

Then the model can answer based on those summaries instead of raw PDF text.

### How to validate whether this fix worked
The fix is working when:
- answers mention multiple distinct mechanisms
- source content from more than one chunk appears in answers
- broad questions stop collapsing into one narrow concept
- answers become broader without becoming generic

---

## 2) Weak source grounding / generic prior override

### What it means
The model sees good LinuxONE-specific context, but instead of using it faithfully, it falls back to its **generic pretrained prior**.

This is what happened in the high-availability example: the source material includes LinuxONE-specific mechanisms such as PR/SM, VSWITCH failover, core sparing, redundant power/cooling, and redundant clocking, but the answer collapsed into a generic description involving load balancing and data replication.

That means the model is overriding source material with a generic concept of “what HA usually means.”

### Why it causes current outputs
The model often prefers:
- a familiar general concept
- broad enterprise phrasing
- a compact abstraction

instead of:
- platform-specific terminology
- mechanism-level details
- direct reuse of retrieved evidence

This happens when retrieval is treated as “helpful context” instead of “primary evidence.”

### How to solve it

#### A. Make context the basis of claims, not a supplement
The system should enforce a rule like:

```text
Every major claim in the answer should be traceable to retrieved context.
```

That can be achieved by:
- generating source-backed notes first
- asking the model to answer only from those evidence notes
- or requiring internal justification/citation for each major point

#### B. Penalize generic prior responses in evaluation
If the answer contains terms such as:
- load balancing
- data replication
- cloud scaling
- GPUs
- AWS/Azure

but those concepts are not in the retrieved chunks, the answer should be flagged as weakly grounded.

#### C. Add a grounding verification step
After generation, run a verification pass such as:

```text
For each major claim in this answer, indicate whether it is supported by a source.
```

If too many unsupported claims appear, the answer should be revised or regenerated.

#### D. Tighten domain interpretation
All user queries in this LinuxONE knowledge assistant should be interpreted as LinuxONE-specific by default unless the user clearly asks otherwise.

This prevents broad prompts like “scaling strategies” from turning into generic cloud or AI scaling answers.

### How to validate whether this fix worked
The fix is working when:
- answers start using the same terminology as the sources
- LinuxONE-specific concepts such as PR/SM, LPAR, VSWITCH, core sparing, N+1 cooling, etc. appear naturally
- generic enterprise boilerplate disappears
- answers feel like they are grounded in the RedBooks rather than in the model’s generic prior

---

## 3) Prompt procedural noncompliance

### What it means
The current prompts already include detailed instructions such as:
- use the RedBook context
- use multiple sources
- be detailed
- be complete
- provide structure
- cite sources

but the model still does not consistently follow those instructions. citeturn31search3

That suggests the model is **not strongly obeying long procedural prompts**.

### Why it causes current outputs
Local instruct models often comply poorly when prompts become:
- too long
- too process-heavy
- too abstract
- too mixed (role + context + procedure + formatting + anti-patterns + verbosity)

The model may follow:
- the role
- the topic
- some high-level style guidance

but still ignore many of the explicit procedural steps.

### How to solve it

#### A. Simplify the prompt and move process into system behavior
Instead of asking the model to do everything inside one prompt:
- detect relevant chunks
- synthesize across them
- structure the answer
- cite sources
- avoid repetition
- avoid generic answers

move some of that work into code.

For example:
- code handles chunk grouping or evidence extraction
- the model receives a more structured evidence representation and a simpler writing task

#### B. Replace natural-language process instructions with structured inputs
Models often perform better when given structured evidence like:

```text
Source 1 - Key facts:
- ...
- ...

Source 2 - Key facts:
- ...
- ...

Question:
...
Task:
Write a LinuxONE-specific answer using these facts.
```

rather than a 10-step procedural instruction block.

#### C. Separate answer style from retrieval procedure
Do not ask one prompt to do both:
- evidence processing
- final writing style

Instead, logically separate:
1. evidence extraction
2. answer drafting

This can still be done within one request if formatted carefully, but separating the concerns usually improves compliance.

#### D. Use shorter, higher-value instructions
Models are more likely to follow instructions such as:
- “Use only supported facts from the evidence summary”
- “Cover all major LinuxONE mechanisms present in the evidence”
- “If a mechanism appears in the evidence, include it”

than a long list of abstract procedural commands.

### How to validate whether this fix worked
The fix is working when:
- behavior becomes more consistent across runs
- citation-like source usage appears more reliably
- the model stops ignoring key instructions
- the output follows the structure of the provided evidence instead of generic prose patterns

---

## 4) Chunk noisiness / fragmentation

### What it means
Even if the **page** is relevant, the actual **chunk** shown to the model may be messy.

The pasted source excerpts show that the pages include:
- relevant prose
- table fragments
- figure captions
- section transitions
- adjacent subtopics

If the chunking process slices that material poorly, the model may see something like:

```text
PR/SM description
Table fragment
Figure caption
Random sentence about OCP node
Hardware note
```

That makes it harder for the model to infer the central point cleanly.

### Why it causes current outputs
Messy chunks cause the model to:
- miss the main idea
- over-index on one clean sentence
- ignore details buried in noise
- produce generic summaries instead of mechanism-level answers

This becomes especially problematic for:
- tables
- figure captions
- technical documents with mixed layout
- PDFs with partial extraction artifacts

### How to solve it

#### A. Improve chunking strategy
Chunks should preserve:
- section boundaries
- sentence coherence
- one core idea per chunk, or at least a tightly related set of ideas

Avoid arbitrary cuts through:
- lists
- headings + body text
- tables
- figure explanations

#### B. Attach structural metadata to chunks
If a chunk comes from a:
- section title
- subsection
- table
- figure caption
- page heading

include that metadata and use it in retrieval or generation.

This helps the system understand whether a chunk is:
- a definition
- a benchmark table
- a resiliency mechanism summary
- a hardware feature overview

#### C. Normalize raw chunk text before sending it to the model
Possible normalization steps include:
- removing repeated headers/footers
- cleaning figure-caption noise
- merging broken lines
- reconstructing bullet lists
- formatting table rows more clearly

#### D. Create LLM-friendly evidence summaries
Instead of passing raw extracted PDF text directly, chunks can be transformed into cleaner evidence summaries:
- key sentences only
- section title + page
- normalized bullet points

### How to validate whether this fix worked
The fix is working when:
- answers become more specific and detailed
- fewer strange generic abstractions appear
- table-heavy or technical sections become easier to answer from
- benchmark-oriented queries start producing benchmark-shaped answers

---

## 5) Retrieval irrelevance / ranking mismatch

### What it means
Even if retrieval is “working,” it may still be retrieving the wrong **kind** of relevant content.

Examples:
- a query about “workload performance benchmarks” may retrieve infrastructure-performance text instead of benchmark-specific text
- a query about “high availability” may retrieve general resiliency passages but miss the most actionably specific mechanism-rich sections
- a query about “hardware capabilities” may over-select Telum-related chunks

### Why it causes current outputs
A RAG pipeline can be **semantically relevant but pragmatically unhelpful**.

This means the chunks are broadly on-theme, but they are not the best chunks for producing a useful answer.

That leads to:
- generic outputs
- wrong emphasis
- incomplete coverage
- source material that does not naturally support the ideal answer

The embedding model being used is a standard sentence-transformers model, which is a reasonable baseline but may not be enough by itself for distinguishing subtle technical intent. citeturn31search2

### How to solve it

#### A. Improve query reformulation
Certain queries are too broad or ambiguous, for example:
- “scaling strategies”
- “hardware capabilities”
- “performance benchmarks”

These should be internally reformulated into more retrieval-friendly forms that better match the technical corpus.

#### B. Classify query intent before retrieval
Map user questions into categories such as:
- architecture
- performance
- availability
- security
- AI tooling
- operations

Then bias retrieval toward sections or documents that are more likely to answer that category.

#### C. Improve reranking criteria
Reranking should not rely only on semantic similarity. It should also consider:
- technical specificity
- section-title relevance
- lexical overlap with key terms
- subtopic diversity

#### D. Prevent topic domination
If 3 out of the top 5 chunks are about Telum but the query is broader, retrieval should rebalance so that one concept does not dominate the final context window.

#### E. Use section-aware retrieval if possible
If chunks carry metadata such as:
- Resiliency
- Performance
- AI Toolkit
- Hardware Architecture

then retrieval can use this to prefer benchmark-oriented sections for benchmark queries, resiliency sections for HA queries, etc.

### How to validate whether this fix worked
The fix is working when:
- the top retrieved chunks look obviously answerable
- responses begin mirroring the right document sections
- “performance benchmark” queries actually surface benchmark-like details
- broad queries return complementary chunks rather than five vague or redundant matches

---

## How the five causes relate to each other

These causes are not isolated. They often form a pipeline of failure like this:

```text
Retrieval mismatch
    ↓
Noisy or weak chunk set
    ↓
Model chooses strongest chunk
    ↓
Fails to synthesize
    ↓
Falls back to generic prior
    ↓
Prompt instructions are ignored or only partially followed
```

So the issue is not necessarily one bug; it is likely a **stacked failure path**.

---

## Recommended prioritization

If these causes are addressed systematically, a reasonable order would be:

### Priority 1 — Retrieval irrelevance / ranking mismatch
If the wrong evidence gets into the context window, everything downstream degrades.

### Priority 2 — Chunk noisiness / fragmentation
Even relevant pages can become weak model inputs if chunked badly.

### Priority 3 — Weak source grounding / generic prior override
This is what causes LinuxONE-specific answers to collapse into generic enterprise prose.

### Priority 4 — Multi-chunk synthesis failure
Once good chunks are present, the model still needs to combine them.

### Priority 5 — Prompt procedural noncompliance
Important, but likely not the primary blocker, since the prompt is already quite explicit and still not being followed consistently. citeturn31search3

---

## Practical debugging framework

For a failing query, inspect the full pipeline end-to-end:

1. **Original user query**
2. **Expanded/reformulated query**
3. **Top raw retrieved chunks**
4. **Final reranked chunks**
5. **Chunk text quality / cleanliness**
6. **Final prompt actually sent to the model**
7. **Raw model output before any continuation/regeneration**
8. **Final displayed answer**

Then score each stage for:
- relevance
- diversity
- chunk cleanliness
- answer grounding
- answer specificity
- source coverage

This will reveal which of the five causes is dominant for each query category.

---

## Final takeaway

The fixes are **not all prompt changes**, and they are **not all code changes either**. The solutions fall into **three layers**:

### 1. Retrieval-layer solutions
- better query reformulation
- better reranking
- better diversity control
- better section awareness

### 2. Evidence-shaping solutions
- cleaner chunking
- chunk normalization
- subtopic grouping
- evidence summarization

### 3. Generation-layer solutions
- stronger source grounding
- less abstract prompting
- answer generation from structured evidence
- source verification / claim grounding

The most important conclusion is:

> The system is not failing because retrieval is completely broken. The system is failing because retrieved evidence is not yet being shaped and used in a way that consistently produces faithful, LinuxONE-specific, multi-source answers.

---

## References

- The embedding layer uses `sentence-transformers/all-MiniLM-L6-v2`, a standard sentence-transformers embedding model used as the retrieval basis in the current pipeline. citeturn31search2
- The current `llm_service.py` prompt already includes instructions about using RedBook context, multiple sources, completeness, and citations, which is why stronger prompt wording alone is unlikely to be the full answer. citeturn31search3

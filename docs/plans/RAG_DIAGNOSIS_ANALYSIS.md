# RAG Issue Diagnosis Analysis & Action Plan

## Overview
This document analyzes the 5 root causes identified in `rag_issue_diagnosis_and_solutions.md` and maps them against our current implementation to identify what's been addressed and what still needs work.

---

## The 5 Root Causes

### 1. Multi-chunk synthesis failure ⚠️ PARTIALLY ADDRESSED
### 2. Weak source grounding / generic prior override ⚠️ PARTIALLY ADDRESSED  
### 3. Prompt procedural noncompliance ⚠️ PARTIALLY ADDRESSED
### 4. Chunk noisiness / fragmentation ❌ NOT ADDRESSED
### 5. Retrieval irrelevance / ranking mismatch ❌ NOT ADDRESSED

---

## Detailed Analysis

### 1️⃣ Multi-chunk synthesis failure

#### What We've Done ✅
- **Added explicit chunk count**: "You have {num_chunks} sources"
- **Mandatory synthesis process**: 5-step process requiring review of ALL sources
- **Citation requirements**: "cite it (e.g., 'According to Source 1...')"
- **Anti-pattern**: "do NOT just use the first relevant source"

#### What's Still Missing ❌
The diagnosis recommends **4 specific solutions** we haven't implemented:

**A. Change task from "answer" to "extract + aggregate + answer"**
```
Current: Direct answer generation
Needed: Step 1: identify relevant chunks
        Step 2: extract bullet facts from each
        Step 3: combine into final answer
```

**B. Group chunks by subtopic before generation**
```
Current: Chunks passed as raw sequence
Needed: Organize into topic groups (e.g., virtualization, networking, hardware)
```

**C. Enforce "coverage dimensions" not just "use multiple sources"**
```
Current: "Use multiple sources"
Needed: "Cover all major relevant dimensions present in context"
        (e.g., for HA: virtualization, failover, hardware sparing, redundancy)
```

**D. Add pre-answer extraction layer**
```
Current: Raw PDF text → LLM
Needed: Raw text → Evidence summaries → LLM
        
Example:
Source 1:
- PR/SM creates isolated LPARs
- supports dynamic allocation
- has automation for HA

Source 2:
- VSWITCH failover
- link aggregation
```

#### Status: ⚠️ PARTIALLY ADDRESSED
We've added enforcement language but haven't changed the **architecture** to force synthesis.

---

### 2️⃣ Weak source grounding / generic prior override

#### What We've Done ✅
- **Context-First prompts**: "Read carefully. This is your PRIMARY source"
- **Explicit grounding**: "BASE your answer on the RedBook context"
- **LinuxONE focus**: "Focus on LinuxONE specifically"
- **Increased detail requirements**: 4-6 paragraphs

#### What's Still Missing ❌
The diagnosis recommends **4 specific solutions** we haven't implemented:

**A. Make context the basis of claims, not a supplement**
```
Current: Prompt says "use context" but doesn't enforce it
Needed: Every major claim must be traceable to retrieved context
        Generate source-backed notes first, then answer from those
```

**B. Penalize generic prior responses in evaluation**
```
Current: No validation of grounding
Needed: Flag answers containing:
        - load balancing, data replication (if not in chunks)
        - cloud scaling, GPUs, AWS/Azure (if not in chunks)
```

**C. Add grounding verification step**
```
Current: No post-generation verification
Needed: After generation, verify:
        "For each major claim, indicate whether it's supported by a source"
```

**D. Tighten domain interpretation**
```
Current: Queries interpreted broadly
Needed: All queries interpreted as LinuxONE-specific by default
```

#### Status: ⚠️ PARTIALLY ADDRESSED
We've strengthened prompts but haven't added **verification** or **enforcement mechanisms**.

---

### 3️⃣ Prompt procedural noncompliance

#### What We've Done ✅
- **Explicit chunk count**: Makes quantity concrete
- **Mandatory language**: "You MUST" instead of "when possible"
- **Step-by-step process**: 5-step synthesis requirement
- **Increased max_tokens**: 2500 (was 1500) for detailed answers

#### What's Still Missing ❌
The diagnosis says: **"The prompt is already quite explicit and still not being followed consistently"**

This means **more prompt changes won't help**. The diagnosis recommends:

**A. Simplify prompt and move process into system behavior**
```
Current: Asking model to do everything in one prompt
Needed: Code handles chunk grouping/evidence extraction
        Model receives structured evidence + simpler writing task
```

**B. Replace natural-language instructions with structured inputs**
```
Current: 10-step procedural instruction block
Needed: Structured evidence format:
        
        Source 1 - Key facts:
        - ...
        Source 2 - Key facts:
        - ...
        
        Task: Write LinuxONE-specific answer using these facts
```

**C. Separate answer style from retrieval procedure**
```
Current: One prompt does both evidence processing + final writing
Needed: Logically separate:
        1. Evidence extraction
        2. Answer drafting
```

**D. Use shorter, higher-value instructions**
```
Current: Long abstract procedural commands
Needed: "Use only supported facts from evidence summary"
        "Cover all major LinuxONE mechanisms present in evidence"
```

#### Status: ⚠️ PARTIALLY ADDRESSED
We've strengthened prompts but the diagnosis says **this won't work** - we need **architectural changes**.

---

### 4️⃣ Chunk noisiness / fragmentation

#### What We've Done ❌
**NOTHING** - This is entirely unaddressed.

#### What's Needed
The diagnosis identifies that chunks may contain:
- Relevant prose
- Table fragments
- Figure captions
- Section transitions
- Adjacent subtopics

**A. Improve chunking strategy**
```
Current: Unknown chunking strategy (need to check)
Needed: Preserve section boundaries, sentence coherence
        Avoid cuts through lists, headings, tables
```

**B. Attach structural metadata to chunks**
```
Current: Chunks have basic metadata (page, section)
Needed: Add metadata for:
        - section title
        - subsection
        - table vs prose
        - figure caption
        - chunk type (definition, benchmark, mechanism, overview)
```

**C. Normalize raw chunk text**
```
Current: Raw PDF extraction
Needed: - Remove repeated headers/footers
        - Clean figure-caption noise
        - Merge broken lines
        - Reconstruct bullet lists
        - Format table rows clearly
```

**D. Create LLM-friendly evidence summaries**
```
Current: Raw PDF text → LLM
Needed: Raw text → Clean summaries → LLM
        - Key sentences only
        - Section title + page
        - Normalized bullet points
```

#### Status: ❌ NOT ADDRESSED
This is a **critical gap** - messy chunks cause the model to miss main ideas and produce generic summaries.

---

### 5️⃣ Retrieval irrelevance / ranking mismatch

#### What We've Done ✅
- **Reranking**: Cross-encoder reranking enabled
- **Diversity filtering**: Prevents redundant chunks
- **Adaptive filtering**: Removes low-quality chunks

#### What's Still Missing ❌
The diagnosis recommends **5 specific solutions**:

**A. Improve query reformulation**
```
Current: Basic query expansion for vague queries
Needed: More sophisticated reformulation:
        "scaling strategies" → "LinuxONE scaling mechanisms, LPAR allocation, workload distribution"
        "hardware capabilities" → "LinuxONE processor features, memory architecture, I/O capabilities"
```

**B. Classify query intent before retrieval**
```
Current: No intent classification
Needed: Map queries to categories:
        - architecture
        - performance
        - availability
        - security
        - AI tooling
        - operations
        Then bias retrieval toward relevant sections
```

**C. Improve reranking criteria**
```
Current: Semantic similarity only
Needed: Also consider:
        - Technical specificity
        - Section-title relevance
        - Lexical overlap with key terms
        - Subtopic diversity
```

**D. Prevent topic domination**
```
Current: No balancing
Needed: If 3/5 chunks are about Telum but query is broader,
        rebalance so one concept doesn't dominate
```

**E. Use section-aware retrieval**
```
Current: Chunks have section metadata but it's not used for retrieval
Needed: Use metadata to prefer:
        - Benchmark sections for benchmark queries
        - Resiliency sections for HA queries
        - Architecture sections for design queries
```

#### Status: ⚠️ PARTIALLY ADDRESSED
We have reranking but not the **sophisticated retrieval improvements** recommended.

---

## The Stacked Failure Path

The diagnosis identifies how these causes compound:

```
Retrieval mismatch (Cause 5)
    ↓
Noisy or weak chunk set (Cause 4)
    ↓
Model chooses strongest chunk (Cause 1)
    ↓
Fails to synthesize (Cause 1)
    ↓
Falls back to generic prior (Cause 2)
    ↓
Prompt instructions ignored (Cause 3)
```

**Key Insight**: We've been attacking Causes 1-3 (generation layer) but haven't addressed Causes 4-5 (retrieval/evidence layer), which are **upstream** and more critical.

---

## Recommended Prioritization (from diagnosis)

### Priority 1 — Retrieval irrelevance / ranking mismatch (Cause 5)
**Status**: ⚠️ Partially addressed
**Why critical**: If wrong evidence gets into context, everything downstream degrades

### Priority 2 — Chunk noisiness / fragmentation (Cause 4)
**Status**: ❌ Not addressed
**Why critical**: Even relevant pages become weak inputs if chunked badly

### Priority 3 — Weak source grounding / generic prior override (Cause 2)
**Status**: ⚠️ Partially addressed
**Why critical**: Causes LinuxONE-specific answers to collapse into generic prose

### Priority 4 — Multi-chunk synthesis failure (Cause 1)
**Status**: ⚠️ Partially addressed
**Why critical**: Once good chunks are present, model still needs to combine them

### Priority 5 — Prompt procedural noncompliance (Cause 3)
**Status**: ⚠️ Partially addressed
**Why less critical**: Prompt is already explicit; more wording won't help

---

## What We've Actually Done

### ✅ Completed
1. **Context-First Hybrid prompts** - Addresses Cause 2 (partially)
2. **Multi-chunk aggregation enforcement** - Addresses Cause 1 (partially)
3. **Explicit chunk count and synthesis process** - Addresses Cause 1 (partially)
4. **Increased max_tokens and temperature** - Addresses Cause 3 (partially)

### ❌ Not Done (Critical Gaps)
1. **Chunk quality improvements** - Cause 4 entirely unaddressed
2. **Evidence extraction/summarization layer** - Causes 1, 2, 4 unaddressed
3. **Query intent classification** - Cause 5 unaddressed
4. **Section-aware retrieval** - Cause 5 unaddressed
5. **Grounding verification** - Cause 2 unaddressed
6. **Structured evidence format** - Causes 1, 3 unaddressed

---

## The Core Problem

The diagnosis concludes:

> **The system is not failing because retrieval is completely broken. The system is failing because retrieved evidence is not yet being shaped and used in a way that consistently produces faithful, LinuxONE-specific, multi-source answers.**

### What This Means
We've been focusing on **generation-layer solutions** (better prompts, more enforcement) but the real issues are in:

1. **Retrieval layer**: Getting the right chunks
2. **Evidence-shaping layer**: Cleaning and structuring chunks
3. **Generation layer**: Using evidence faithfully

We've only addressed #3, and even that incompletely.

---

## Recommended Next Steps

### Phase 1: Evidence Shaping (Highest Impact)
**Goal**: Transform raw chunks into clean, structured evidence

1. **Implement evidence extraction layer**
   - Convert each chunk into bullet-point facts
   - Remove noise (headers, footers, figure captions)
   - Normalize formatting

2. **Add chunk metadata enrichment**
   - Classify chunks (definition, mechanism, benchmark, overview)
   - Extract section hierarchy
   - Identify chunk type (prose, table, list)

3. **Create structured evidence format**
   ```
   Source 1 (Resiliency, Page 45):
   - PR/SM creates isolated LPARs
   - Supports dynamic allocation
   
   Source 2 (Networking, Page 67):
   - VSWITCH failover
   - Link aggregation
   ```

### Phase 2: Retrieval Improvements (High Impact)
**Goal**: Get better chunks into the context window

1. **Implement query intent classification**
   - Categorize queries (architecture, performance, HA, security, AI)
   - Bias retrieval toward relevant sections

2. **Improve query reformulation**
   - Make vague queries more specific
   - Add LinuxONE-specific terminology

3. **Add section-aware retrieval**
   - Use chunk metadata to prefer relevant sections
   - Prevent topic domination (e.g., too many Telum chunks)

### Phase 3: Generation Improvements (Medium Impact)
**Goal**: Ensure faithful use of evidence

1. **Simplify prompts with structured inputs**
   - Replace long procedural instructions
   - Use structured evidence format
   - Shorter, clearer instructions

2. **Add grounding verification**
   - Post-generation check: are claims supported?
   - Flag generic prior responses
   - Regenerate if grounding is weak

3. **Implement extract-then-answer architecture**
   - Step 1: Extract facts from each source
   - Step 2: Synthesize facts into answer
   - Step 3: Verify grounding

---

## Success Metrics

### For Evidence Shaping
- Chunks are clean and readable
- Each chunk has clear metadata
- Evidence summaries are concise and accurate

### For Retrieval
- Top chunks are obviously answerable
- Benchmark queries surface benchmark sections
- Broad queries return complementary (not redundant) chunks

### For Generation
- Answers cite multiple sources
- LinuxONE-specific terminology appears naturally
- Generic enterprise boilerplate disappears
- Answers are 4-6 paragraphs with structure

---

## Conclusion

**We've been treating symptoms (weak prompts) instead of root causes (poor evidence quality and retrieval).**

The diagnosis is clear: **The fixes are not all prompt changes**. They fall into three layers:

1. **Retrieval-layer solutions** (Priority 1-2) - ❌ Mostly unaddressed
2. **Evidence-shaping solutions** (Priority 2) - ❌ Entirely unaddressed  
3. **Generation-layer solutions** (Priority 3-5) - ⚠️ Partially addressed

**Next action**: Implement evidence extraction/summarization layer as the highest-impact improvement.

---

*Analysis based on `rag_issue_diagnosis_and_solutions.md`*
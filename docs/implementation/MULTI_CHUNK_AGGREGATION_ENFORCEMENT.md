# Multi-Chunk Aggregation Enforcement

## Problem Identified
The system was failing to produce detailed answers because the LLM was treating retrieved chunks as **optional references** rather than sources to be synthesized. The behavior was:

```
retrieve → pass chunks → LLM picks 1 → stop
```

This resulted in:
- ❌ Answers based on only one chunk
- ❌ Shallow responses missing information from other chunks
- ❌ No synthesis across multiple sources
- ❌ Incomplete coverage of the topic

## Root Cause
**Aggregation Enforcement Problem**: The system had no mechanism to enforce synthesis. Chunks were presented as optional, and the LLM could satisfy the prompt by using just the first relevant chunk.

---

## Solution: Multi-Chunk Aggregation Enforcement

### New Architecture
```
retrieve → force multi-chunk use → LLM aggregates → expanded answer
```

### Two-Level Enforcement

#### 1. Code-Level Changes
**Before**: Chunks presented as optional references
```python
context_text = "\n\n".join(context_parts)
# LLM sees: "Here's some context..."
```

**After**: Chunks presented with explicit count and synthesis requirement
```python
num_chunks = len(context_chunks)
# LLM sees: "You have 5 sources. You MUST synthesize from ALL..."
```

#### 2. Prompt-Level Changes
**Before**: Weak suggestion
```
"Use information from MULTIPLE sources when possible"
```

**After**: Mandatory synthesis process
```
IMPORTANT: You have been provided with {num_chunks} different sources.
You MUST synthesize information from ALL relevant sources.

MANDATORY SYNTHESIS PROCESS:
1. Review ALL {num_chunks} sources above - do not skip any
2. Identify which sources contain information relevant to the question
3. Extract key points from EACH relevant source
4. Synthesize these points into a coherent answer
5. Your answer MUST reference multiple sources when they contain relevant information
```

---

## Implementation Details

### Main Prompt Changes (`_build_prompt`)

#### Comprehensive Mode
```python
num_chunks = len(context_chunks)

prompt = f"""You are an expert assistant for IBM LinuxONE.

IMPORTANT: You have been provided with {num_chunks} different sources from LinuxONE RedBooks below. 
You MUST synthesize information from ALL relevant sources to provide a complete answer.

Read ALL {num_chunks} sources carefully - each provides different aspects of the answer:

{context_text}

User question:
{query}

MANDATORY SYNTHESIS PROCESS:
1. Review ALL {num_chunks} sources above - do not skip any
2. Identify which sources contain information relevant to the question
3. Extract key points from EACH relevant source
4. Synthesize these points into a coherent, comprehensive answer
5. Your answer MUST reference multiple sources when they contain relevant information

Instructions for your answer:
- Provide a DETAILED and COMPLETE explanation with clear structure
- When using information from a source, cite it (e.g., "According to Source 1...")
- Combine information from multiple sources - do NOT just use the first relevant source
- Be thorough - provide 4-6 paragraphs or structured sections
```

#### Focused Mode
Same structure but adapted for specific queries:
```python
IMPORTANT: You have been provided with {num_chunks} different sources.
You MUST synthesize information from ALL relevant sources.

MANDATORY SYNTHESIS PROCESS:
1. Review ALL {num_chunks} sources above - do not skip any
2. Identify which sources contain information relevant to the question
3. Extract key points from EACH relevant source
4. Synthesize these points into a coherent answer
5. Your answer MUST reference multiple sources when they contain relevant information
```

### Continuation Prompt Changes
```python
You have {num_chunks} sources from LinuxONE RedBooks. Review ALL of them to complete your answer:

Instructions:
- Review ALL {num_chunks} sources above for additional information
- Synthesize information from multiple sources if they contain relevant details
- Cite sources when adding new information (e.g., "Source 2 also indicates...")
```

### Regeneration Prompt Changes
```python
You have {num_chunks} sources from LinuxONE RedBooks. 
Review and synthesize information from ALL relevant sources:

MANDATORY SYNTHESIS:
1. Review ALL {num_chunks} sources above
2. Identify relevant information in each source
3. Synthesize into a complete answer
4. Cite sources when using their information
```

---

## Key Enforcement Mechanisms

### 1. Explicit Chunk Count
**Before**: No mention of how many sources exist
**After**: "You have {num_chunks} sources" - makes quantity explicit

### 2. Mandatory Language
**Before**: "when possible", "if relevant"
**After**: "You MUST", "MANDATORY SYNTHESIS PROCESS"

### 3. Step-by-Step Process
Forces the LLM to:
1. Review ALL sources (not just first one)
2. Identify relevant information in EACH
3. Extract key points from EACH
4. Synthesize (not just copy from one)
5. Reference multiple sources

### 4. Citation Requirement
**Before**: Optional source mentions
**After**: "When using information from a source, cite it"

### 5. Explicit Anti-Pattern
**After**: "do NOT just use the first relevant source"

---

## Expected Behavior Changes

### Before Multi-Chunk Enforcement
```
Query: "Hardware capabilities"
Retrieval: 5 chunks about different aspects
LLM behavior: Reads Source 1 (processors), answers based only on that
Result: Short answer about processors only
```

### After Multi-Chunk Enforcement
```
Query: "Hardware capabilities"
Retrieval: 5 chunks about different aspects
LLM behavior: 
  1. Reviews all 5 sources
  2. Identifies: Source 1 (processors), Source 2 (memory), Source 3 (I/O), 
     Source 4 (security), Source 5 (performance)
  3. Synthesizes comprehensive answer covering all aspects
  4. Cites each source when using its information
Result: Detailed answer with 4-6 paragraphs covering all hardware aspects
```

---

## Testing Checklist

### Test 1: Multi-Aspect Query
**Query**: "Hardware capabilities"
**Expected**: 
- Answer should reference multiple sources (e.g., "Source 1 describes..., Source 2 indicates...")
- Should cover multiple aspects (processors, memory, I/O, security)
- Should be 4-6 paragraphs
- Should NOT focus on just one component

### Test 2: Specific Query with Multiple Sources
**Query**: "How does LinuxONE handle encryption?"
**Expected**:
- Should synthesize from multiple sources if they discuss different encryption aspects
- Should cite sources (e.g., "According to Source 1... Source 3 also mentions...")
- Should be detailed and complete

### Test 3: Broad Query
**Query**: "What is LinuxONE?"
**Expected**:
- Should use information from all relevant sources
- Should have structured sections (Overview, Features, Architecture, Benefits)
- Each section should draw from multiple sources
- Should be 4-6 paragraphs minimum

---

## Monitoring

### Metrics to Track
1. **Source Usage Distribution**
   - How many sources are cited per answer?
   - Are answers using only 1 source or multiple?

2. **Answer Length**
   - Average paragraph count
   - Token count distribution

3. **Citation Patterns**
   - Frequency of "Source 1", "Source 2", etc. in answers
   - Percentage of answers citing multiple sources

### Log Analysis
```bash
# Count source citations in answers
grep -o "Source [0-9]" backend.log | sort | uniq -c

# Check for multi-source usage
grep "Source 1.*Source 2" backend.log | wc -l

# Average answer length
grep "completion_tokens" backend.log | awk '{sum+=$NF; count++} END {print sum/count}'
```

---

## Files Modified

1. **`backend/app/services/llm_service.py`**
   - `_build_prompt()`: Added `num_chunks` calculation and mandatory synthesis process
   - `_build_continuation_prompt()`: Added multi-chunk enforcement
   - `_build_regenerate_prompt()`: Added multi-chunk enforcement

---

## Comparison: Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| **Chunk Presentation** | Optional references | Explicit count + mandatory synthesis |
| **Synthesis Instruction** | "when possible" | "MANDATORY SYNTHESIS PROCESS" |
| **Source Review** | Implicit | "Review ALL {num_chunks} sources" |
| **Citation** | Optional | Required with examples |
| **Anti-Pattern** | None | "do NOT just use first source" |
| **Process Steps** | None | 5-step mandatory process |
| **Expected Behavior** | Pick 1 chunk → answer | Review all → synthesize → cite |

---

## Success Criteria

- [x] Explicit chunk count added to all prompts
- [x] Mandatory synthesis process defined
- [x] Citation requirements added
- [x] Anti-pattern explicitly stated
- [x] Step-by-step process enforced
- [ ] Testing confirms multi-source usage
- [ ] Answers reference multiple sources
- [ ] Answer detail level increased

---

## Next Steps

1. **Test with sample queries** to verify:
   - Multiple sources are being cited
   - Answers synthesize across chunks
   - Detail level has increased

2. **Monitor in production**:
   - Track source citation patterns
   - Measure answer length distribution
   - Collect user feedback on completeness

3. **Iterate if needed**:
   - Strengthen enforcement if still seeing single-source answers
   - Adjust chunk count if too many/few sources
   - Refine synthesis instructions based on results

---

**Status**: ✅ Implementation Complete  
**Testing**: ⏳ Ready for Validation  
**Expected Impact**: Detailed, multi-source synthesized answers instead of shallow single-chunk responses

---

*Multi-Chunk Aggregation: From Optional References to Mandatory Synthesis*
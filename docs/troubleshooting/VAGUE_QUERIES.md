RAG Improvements: Vague Query Handling + Structured Answers
🎯 Goal
Improve response quality for vague queries (e.g., “What is LinuxONE?”) by:

Expanding queries before retrieval
Improving context coverage
Forcing structured, detailed answers


✅ Change 1: Query Expansion (Retrieval Stage)
📍 Where
In the retrieval function (before embeddings / vector search)
✅ What to add
Pythondef is_vague_query(query: str) -> bool:    q = query.lower().strip()    return (        len(q.split()) <= 4 or        q.startswith("what is") or        q.startswith("define") or        q.startswith("explain")    )def expand_query(query: str) -> str:    if is_vague_query(query):        return query + " overview features architecture components benefits use cases LinuxONE platform"    return queryShow more lines
✅ Modify retrieval logic
Before:
Pythonembedding = embed(query)Show more lines
After:
Pythonquery_for_search = expand_query(query)embedding = embed(query_for_search)``Show more lines
✅ Effect

Improves retrieval coverage
Fetches diverse chunks (features, architecture, use cases)
Reduces shallow answers


✅ Change 2: Prompt Mode Switching (LLM Stage)
📍 Where
In the file where you build the LLM prompt (qwen_client.py or similar)
✅ What to add
Pythonif is_vague_query(query):    answer_mode = "comprehensive"else:    answer_mode = "focused"``Show more lines
✅ Update prompt
Replace existing instructions with:
Pythonprompt = f"""You are an expert LinuxONE assistant.Mode: {answer_mode}If Mode = comprehensive:- Provide a detailed, structured answer- ALWAYS include:  - Overview  - Key Features  - Architecture / Components  - Benefits / Use Cases- Use bullet points in each section- Expand the answer even if the question is simpleIf Mode = focused:- Answer only the specific questionRules:- Use only the provided context- Do not repeat similar points- Combine similar ideas into one bullet- If information is missing, say "Limited information available"Context:{context}Question:{query}"""Show more lines
✅ Effect

Ensures consistent structured output
Prevents short/paragraph-only answers
Makes vague queries produce rich, multi-section responses


✅ Change 3: Keep Original Query for LLM
⚠️ Important
Do NOT pass the expanded query to the LLM.
✅ Correct behavior
Python# Retrieval uses expanded queryquery_for_search = expand_query(user_query)# LLM uses original queryquestion = user_queryShow more lines
❌ Incorrect (avoid)
PythonQuestion: What is LinuxONE features architecture benefits use cases``Show more lines
✅ Correct
PythonQuestion: What is LinuxONE?Show more lines
✅ Effect

Maintains natural user intent
Avoids confusing the model
Keeps answers clean and readable


🧠 Summary
After applying all 3 changes:
Before

Vague queries → inconsistent, shallow answers
Model relies too much on prompt wording

After

Vague queries automatically become:

richer retrieval ✅
structured responses ✅
consistent outputs ✅




🚀 Final Pipeline (Updated)
User Query
   ↓
[NEW] Detect vague query
   ↓
[NEW] Expand query for retrieval
   ↓
Vector Search + Filtering
   ↓
[NEW] Set answer mode (comprehensive / focused)
   ↓
LLM with structured prompt
   ↓
Final Answer (consistent + detailed)


✅ Optional Quick Test
Run:
What is LinuxONE?

✅ Expected output:

Overview section
Bullet-point features
Architecture details
Use cases